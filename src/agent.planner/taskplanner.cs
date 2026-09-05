using Microsoft.Extensions.Logging;

namespace agent.planner;

/// <summary>
/// 任务规划器实现
/// </summary>
public class TaskPlanner : ITaskPlanner
{
    private readonly ILogger<TaskPlanner> _logger;
    private readonly Dictionary<string, TaskGraph> _plans = new();
    private readonly Dictionary<string, ExecutionContext> _contexts = new();
    private readonly object _lock = new();
    
    public TaskPlanner(ILogger<TaskPlanner> logger)
    {
        _logger = logger;
    }
    
    public Task<TaskGraph> CreatePlanAsync(string description, CancellationToken ct = default)
    {
        var plan = new TaskGraph
        {
            Name = description,
            CreatedAt = DateTime.UtcNow,
            Status = PlanStatus.Created
        };
        
        // 创建根任务
        var rootTask = new TaskNode
        {
            Name = "Root",
            Description = description,
            Priority = TaskPriority.Critical,
            Status = TaskStatus.Pending
        };
        
        plan.Nodes[rootTask.Id] = rootTask;
        plan.RootTaskId = rootTask.Id;
        
        lock (_lock)
        {
            _plans[plan.Id] = plan;
            _contexts[plan.Id] = new ExecutionContext
            {
                PlanId = plan.Id,
                StartTime = DateTime.UtcNow
            };
        }
        
        _logger.LogInformation("Created plan {PlanId}: {Description}", plan.Id, description);
        
        return Task.FromResult(plan);
    }
    
    public Task<TaskNode> AddTaskAsync(string planId, TaskNode task, CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (!_plans.TryGetValue(planId, out var plan))
            {
                throw new InvalidOperationException($"Plan not found: {planId}");
            }
            
            task.CreatedAt = DateTime.UtcNow;
            plan.Nodes[task.Id] = task;
            
            // 添加依赖关系
            foreach (var depId in task.Dependencies)
            {
                if (plan.Nodes.TryGetValue(depId, out var depTask))
                {
                    if (!depTask.Dependents.Contains(task.Id))
                    {
                        depTask.Dependents.Add(task.Id);
                    }
                }
            }
        }
        
        _logger.LogDebug("Added task {TaskId} to plan {PlanId}", task.Id, planId);
        
        return Task.FromResult(task);
    }
    
    public Task<DependencyAnalysis> AnalyzeDependenciesAsync(string planId, CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (!_plans.TryGetValue(planId, out var plan))
            {
                throw new InvalidOperationException($"Plan not found: {planId}");
            }
            
            var analysis = new DependencyAnalysis();
            var visited = new HashSet<string>();
            var stack = new Stack<string>();
            
            // 拓扑排序
            var inDegree = new Dictionary<string, int>();
            foreach (var node in plan.Nodes.Values)
            {
                inDegree[node.Id] = node.Dependencies.Count;
                
                if (node.Dependencies.Count == 0)
                {
                    analysis.RootTasks.Add(node.Id);
                }
            }
            
            // BFS拓扑排序
            var queue = new Queue<string>();
            foreach (var root in analysis.RootTasks)
            {
                queue.Enqueue(root);
            }
            
            var level = 0;
            while (queue.Count > 0)
            {
                var levelNodes = new List<string>();
                var count = queue.Count;
                
                for (int i = 0; i < count; i++)
                {
                    var nodeId = queue.Dequeue();
                    analysis.Levels[level] = levelNodes;
                    
                    if (!plan.Nodes.TryGetValue(nodeId, out var node))
                        continue;
                    
                    levelNodes.Add(nodeId);
                    
                    foreach (var dependentId in node.Dependents)
                    {
                        if (--inDegree[dependentId] == 0)
                        {
                            queue.Enqueue(dependentId);
                        }
                        
                        analysis.Edges.Add((nodeId, dependentId));
                    }
                    
                    visited.Add(nodeId);
                }
                
                level++;
            }
            
            // 检测叶子节点
            foreach (var node in plan.Nodes.Values)
            {
                if (node.Dependents.Count == 0)
                {
                    analysis.LeafTasks.Add(node.Id);
                }
            }
            
            // 检测循环
            foreach (var node in plan.Nodes.Values)
            {
                if (!visited.Contains(node.Id))
                {
                    var cycle = new List<string>();
                    DetectCycle(plan, node.Id, new HashSet<string>(), cycle);
                    if (cycle.Count > 0)
                    {
                        analysis.Cycles.Add(string.Join(" -> ", cycle));
                    }
                }
            }
            
            return Task.FromResult(analysis);
        }
    }
    
    public async Task<ExecutionResult> ExecuteAsync(string planId, CancellationToken ct = default)
    {
        var result = new ExecutionResult { Duration = TimeSpan.Zero };
        var startTime = DateTime.UtcNow;
        
        TaskGraph plan;
        ExecutionContext context;
        
        lock (_lock)
        {
            if (!_plans.TryGetValue(planId, out plan!))
            {
                throw new InvalidOperationException($"Plan not found: {planId}");
            }
            
            if (!_contexts.TryGetValue(planId, out context!))
            {
                throw new InvalidOperationException($"Context not found: {planId}");
            }
            
            plan.Status = PlanStatus.Executing;
        }
        
        try
        {
            var analysis = await AnalyzeDependenciesAsync(planId, ct);
            
            if (analysis.HasCycles)
            {
                result.Error = $"Plan contains circular dependencies: {string.Join(", ", analysis.Cycles)}";
                result.Success = false;
                return result;
            }
            
            // 按层级执行
            foreach (var (level, taskIds) in analysis.Levels.OrderBy(l => l.Key))
            {
                ct.ThrowIfCancellationRequested();
                
                var levelTasks = taskIds
                    .Where(id => plan.Nodes.TryGetValue(id, out var node) && 
                                node.Status == TaskStatus.Pending &&
                                node.Dependencies.All(depId => 
                                    plan.Nodes.TryGetValue(depId, out var dep) && 
                                    dep.Status == TaskStatus.Completed))
                    .ToList();
                
                // 并行执行同层任务
                var tasks = levelTasks.Select(async taskId =>
                {
                    var task = plan.Nodes[taskId];
                    return await ExecuteTaskAsync(plan, context, task, ct);
                });
                
                var taskResults = await Task.WhenAll(tasks);
                
                foreach (var taskResult in taskResults)
                {
                    if (taskResult.Success)
                    {
                        result.CompletedTasks.Add(taskResult.Task);
                        context.CompletedTaskIds.Add(taskResult.Task.Id);
                    }
                    else
                    {
                        result.FailedTasks.Add(taskResult.Task);
                        context.FailedTaskIds.Add(taskResult.Task.Id);
                        
                        // 如果失败的任务是关键任务，终止执行
                        if (taskResult.Task.Priority == TaskPriority.Critical)
                        {
                            result.Error = $"Critical task failed: {taskResult.Task.Name}";
                            result.Success = false;
                            plan.Status = PlanStatus.Failed;
                            return result;
                        }
                    }
                }
            }
            
            plan.Status = PlanStatus.Completed;
            plan.CompletedAt = DateTime.UtcNow;
            result.Success = true;
        }
        catch (OperationCanceledException)
        {
            plan.Status = PlanStatus.Cancelled;
            result.Success = false;
            result.Error = "Execution cancelled";
        }
        catch (Exception ex)
        {
            plan.Status = PlanStatus.Failed;
            result.Success = false;
            result.Error = ex.Message;
            _logger.LogError(ex, "Plan execution failed: {PlanId}", planId);
        }
        
        result.Duration = DateTime.UtcNow - startTime;
        return result;
    }
    
    public Task PauseAsync(string planId, CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (_plans.TryGetValue(planId, out var plan))
            {
                plan.Status = PlanStatus.Paused;
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task ResumeAsync(string planId, CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (_plans.TryGetValue(planId, out var plan))
            {
                plan.Status = PlanStatus.Executing;
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task CancelAsync(string planId, CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (_plans.TryGetValue(planId, out var plan))
            {
                plan.Status = PlanStatus.Cancelled;
                
                foreach (var node in plan.Nodes.Values.Where(n => n.Status == TaskStatus.Pending || n.Status == TaskStatus.InProgress))
                {
                    node.Status = TaskStatus.Cancelled;
                }
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task<TaskGraph?> GetPlanAsync(string planId, CancellationToken ct = default)
    {
        lock (_lock)
        {
            _plans.TryGetValue(planId, out var plan);
            return Task.FromResult(plan);
        }
    }
    
    public Task<PlanValidation> ValidateAsync(string planId, CancellationToken ct = default)
    {
        var validation = new PlanValidation { IsValid = true };
        
        lock (_lock)
        {
            if (!_plans.TryGetValue(planId, out var plan))
            {
                validation.IsValid = false;
                validation.Errors.Add("Plan not found");
                return Task.FromResult(validation);
            }
            
            // 检查是否有任务
            if (plan.Nodes.Count == 0)
            {
                validation.IsValid = false;
                validation.Errors.Add("Plan has no tasks");
            }
            
            // 检查无效的依赖
            foreach (var node in plan.Nodes.Values)
            {
                foreach (var depId in node.Dependencies)
                {
                    if (!plan.Nodes.ContainsKey(depId))
                    {
                        validation.Errors.Add($"Task {node.Name} depends on non-existent task: {depId}");
                        validation.IsValid = false;
                    }
                }
            }
            
            // 检查循环依赖
            var analysis = AnalyzeDependenciesAsync(planId, ct).Result;
            if (analysis.HasCycles)
            {
                validation.Errors.Add($"Circular dependencies detected: {string.Join(", ", analysis.Cycles)}");
                validation.IsValid = false;
            }
            
            // 提供建议
            if (plan.Nodes.Count > 20)
            {
                validation.Suggestions.Add("Consider breaking down large plans into smaller sub-plans");
            }
            
            // 检查孤立任务
            var rootTasks = analysis.RootTasks;
            if (rootTasks.Count > 5)
            {
                validation.Warnings.Add($"Many root tasks ({rootTasks.Count}) may indicate incomplete task decomposition");
            }
        }
        
        return Task.FromResult(validation);
    }
    
    public Task CreateCheckpointAsync(string planId, string taskId, string checkpointName, CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (_plans.TryGetValue(planId, out var plan) && plan.Nodes.TryGetValue(taskId, out var task))
            {
                var checkpoint = new TaskCheckpoint
                {
                    Name = checkpointName,
                    State = new Dictionary<string, object>(task.Metadata),
                    CreatedAt = DateTime.UtcNow
                };
                
                task.Checkpoints.Add(checkpoint);
            }
        }
        
        return Task.CompletedTask;
    }
    
    public Task RecoveryAsync(string planId, string checkpointId, CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (!_plans.TryGetValue(planId, out var plan))
            {
                throw new InvalidOperationException($"Plan not found: {planId}");
            }
            
            foreach (var node in plan.Nodes.Values)
            {
                var checkpoint = node.Checkpoints.FirstOrDefault(c => c.Id == checkpointId);
                if (checkpoint != null)
                {
                    // 恢复状态
                    node.Metadata = new Dictionary<string, object>(checkpoint.State);
                    node.Status = TaskStatus.Pending;
                    
                    // 将后续任务也标记为待处理
                    foreach (var dependentId in node.Dependents)
                    {
                        if (plan.Nodes.TryGetValue(dependentId, out var dependent))
                        {
                            dependent.Status = TaskStatus.Pending;
                        }
                    }
                    
                    break;
                }
            }
        }
        
        return Task.CompletedTask;
    }
    
    private async Task<(bool Success, TaskNode Task)> ExecuteTaskAsync(
        TaskGraph plan, 
        ExecutionContext context, 
        TaskNode task, 
        CancellationToken ct)
    {
        task.Status = TaskStatus.InProgress;
        task.StartedAt = DateTime.UtcNow;
        
        _logger.LogInformation("Executing task {TaskId}: {TaskName}", task.Id, task.Name);
        
        try
        {
            // 模拟任务执行（实际实现中会调用具体任务处理器）
            await Task.Delay(100, ct);
            
            task.Status = TaskStatus.Completed;
            task.CompletedAt = DateTime.UtcNow;
            task.Result = $"Task '{task.Name}' completed successfully";
            
            _logger.LogInformation("Task {TaskId} completed", task.Id);
            
            return (true, task);
        }
        catch (Exception ex)
        {
            task.Status = TaskStatus.Failed;
            task.Error = ex.Message;
            task.CompletedAt = DateTime.UtcNow;
            
            _logger.LogError(ex, "Task {TaskId} failed", task.Id);
            
            return (false, task);
        }
    }
    
    private void DetectCycle(TaskGraph plan, string nodeId, HashSet<string> visiting, List<string> cycle)
    {
        if (visiting.Contains(nodeId))
        {
            cycle.Add(nodeId);
            return;
        }
        
        if (!plan.Nodes.TryGetValue(nodeId, out var node))
            return;
        
        visiting.Add(nodeId);
        cycle.Add(nodeId);
        
        foreach (var depId in node.Dependencies)
        {
            DetectCycle(plan, depId, visiting, cycle);
            if (cycle.Count > 0) return;
        }
        
        visiting.Remove(nodeId);
        cycle.Remove(nodeId);
    }
}
