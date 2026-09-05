using Microsoft.Extensions.Logging;
using agent.core;
using agent.workspace;
using agent.subagent;
using agent.recovery;

namespace agent.planner;

/// <summary>
/// 任务执行引擎 - 工业级任务循环
/// </summary>
public class TaskExecutionEngine
{
    private readonly ILogger<TaskExecutionEngine> _logger;
    private readonly IInteractionManager _interactionManager;
    private readonly IFeedbackStore _feedbackStore;
    private readonly ISubAgentPool _subAgentPool;
    private readonly IRecoverySystem _recoverySystem;
    private readonly IWorkspace _workspace;
    
    public TaskExecutionEngine(
        ILogger<TaskExecutionEngine> logger,
        IInteractionManager interactionManager,
        IFeedbackStore feedbackStore,
        ISubAgentPool subAgentPool,
        IRecoverySystem recoverySystem,
        IWorkspace workspace)
    {
        _logger = logger;
        _interactionManager = interactionManager;
        _feedbackStore = feedbackStore;
        _subAgentPool = subAgentPool;
        _recoverySystem = recoverySystem;
        _workspace = workspace;
    }
    
    /// <summary>
    /// 执行任务（带用户互动）
    /// </summary>
    public async Task<TaskExecutionResult> ExecuteAsync(
        string taskDescription,
        ExecutionOptions options,
        IProgress<ExecutionProgress>? progress = null,
        CancellationToken ct = default)
    {
        var result = new TaskExecutionResult
        {
            TaskDescription = taskDescription
        };
        
        try
        {
            // 1. 任务规划阶段 - 创建任务图
            _logger.LogInformation("Phase 1: Planning task...");
            var plan = await CreatePlanAsync(taskDescription, options, ct);
            result.PlanId = plan.Id;
            
            // 2. 确认阶段 - 与用户确认
            _logger.LogInformation("Phase 2: User confirmation...");
            var confirmed = await ConfirmWithUserAsync(plan, options, ct);
            
            if (!confirmed)
            {
                result.Status = ExecutionStatus.Aborted;
                result.AbortReason = "User cancelled";
                return result;
            }
            
            // 3. 执行阶段 - SubAgent执行
            _logger.LogInformation("Phase 3: Executing with SubAgents...");
            progress?.Report(new ExecutionProgress("开始执行任务...", 0));
            
            await ExecuteWithSubAgentsAsync(plan, options, progress, ct);
            
            // 4. 结果确认阶段 - 与用户确认结果
            _logger.LogInformation("Phase 4: Result confirmation...");
            var approved = await ConfirmResultAsync(plan, options, ct);
            
            result.Status = approved ? ExecutionStatus.Completed : ExecutionStatus.NeedsRevision;
            
            // 5. 保存反馈到RAG
            _logger.LogInformation("Phase 5: Saving feedback to RAG...");
            await SaveFeedbackAsync(plan, result, ct);
            
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Task execution failed");
            result.Status = ExecutionStatus.Failed;
            result.Error = ex.Message;
            
            // 尝试恢复
            var recoveryActions = await _recoverySystem.GetRecoveryActionsAsync(ex.Message);
            result.RecoveryOptions = recoveryActions;
            
            return result;
        }
    }
    
    /// <summary>
    /// 创建任务计划
    /// </summary>
    private async Task<TaskGraph> CreatePlanAsync(string taskDescription, ExecutionOptions options, CancellationToken ct)
    {
        var planner = new TaskPlanner(_logger as ILogger<TaskPlanner> ?? LoggerFactory.Create(b => b.AddConsole()).CreateLogger<TaskPlanner>());
        
        // 创建计划
        var plan = await planner.CreatePlanAsync(taskDescription, ct);
        
        // 分析任务并拆分为子任务
        var subTasks = DecomposeIntoSubTasks(taskDescription);
        
        foreach (var (taskName, taskDetails, subAgentType) in subTasks)
        {
            var task = new TaskNode
            {
                Name = taskName,
                Description = taskDetails,
                SubAgentType = subAgentType,
                Priority = TaskPriority.Normal
            };
            
            await planner.AddTaskAsync(plan.Id, task, ct);
        }
        
        return plan;
    }
    
    /// <summary>
    /// 拆分任务为SubTask
    /// </summary>
    private List<(string Name, string Details, SubAgentType Type)> DecomposeIntoSubTasks(string taskDescription)
    {
        var tasks = new List<(string Name, string Details, SubAgentType Type)>();
        
        var lowerTask = taskDescription.ToLowerInvariant();
        
        // 分析任务类型并拆分
        if (lowerTask.Contains("创建") || lowerTask.Contains("生成"))
        {
            tasks.Add(("分析需求", "理解用户需求，确定代码结构", SubAgentType.Coder));
            tasks.Add(("生成代码", "根据需求生成代码", SubAgentType.Coder));
            tasks.Add(("生成测试", "为生成的代码编写测试", SubAgentType.Tester));
            tasks.Add(("代码审查", "审查生成的代码质量", SubAgentType.Reviewer));
        }
        else if (lowerTask.Contains("修改") || lowerTask.Contains("重构"))
        {
            tasks.Add(("分析现有代码", "理解现有代码结构", SubAgentType.Coder));
            tasks.Add(("制定修改计划", "确定修改范围和影响", SubAgentType.Planner));
            tasks.Add(("执行修改", "按计划修改代码", SubAgentType.Coder));
            tasks.Add(("验证修改", "运行测试验证修改", SubAgentType.Tester));
        }
        else if (lowerTask.Contains("审查") || lowerTask.Contains("review"))
        {
            tasks.Add(("收集代码", "收集要审查的代码文件", SubAgentType.Coder));
            tasks.Add(("静态分析", "进行静态代码分析", SubAgentType.Reviewer));
            tasks.Add(("生成报告", "生成审查报告", SubAgentType.Reviewer));
        }
        else
        {
            // 默认流程
            tasks.Add(("理解任务", "理解用户任务要求", SubAgentType.Researcher));
            tasks.Add(("执行任务", "执行具体任务", SubAgentType.Coder));
            tasks.Add(("验证结果", "验证任务结果", SubAgentType.Tester));
        }
        
        return tasks;
    }
    
    /// <summary>
    /// 与用户确认
    /// </summary>
    private async Task<bool> ConfirmWithUserAsync(TaskGraph plan, ExecutionOptions options, CancellationToken ct)
    {
        // 创建确认交互点
        var interaction = await _interactionManager.CreateInteractionAsync(
            taskId: plan.RootTaskId,
            type: InteractionPointType.TaskConfirmation,
            title: "任务确认",
            message: $"我将执行以下任务:\n\n{plan.Name}\n\n包含 {plan.Nodes.Count} 个步骤:\n" +
                     string.Join("\n", plan.Nodes.Values.Select(n => $"• {n.Name}")),
            options: new List<InteractionOption>
            {
                new() { Id = "proceed", Label = "开始执行", IsRecommended = true },
                new() { Id = "modify", Label = "修改任务" },
                new() { Id = "cancel", Label = "取消任务" }
            },
            isRequired: true
        );
        
        // 等待用户响应
        var response = await _interactionManager.WaitForResponseAsync(interaction.Id, ct);
        
        if (response == null)
        {
            _logger.LogWarning("User did not respond to confirmation");
            return false;
        }
        
        // 存储反馈
        await _feedbackStore.StoreAsync(new UserFeedback
        {
            TaskId = plan.RootTaskId,
            InteractionId = interaction.Id,
            SelectedOptionId = response.SelectedOptionId ?? "timeout",
            SelectedOptionLabel = response.Options.FirstOrDefault(o => o.Id == response.SelectedOptionId)?.Label,
            UserComment = response.UserComment,
            TaskDescription = plan.Name,
            Context = plan.Name
        });
        
        return response.SelectedOptionId == "proceed";
    }
    
    /// <summary>
    /// 使用SubAgent执行
    /// </summary>
    private async Task ExecuteWithSubAgentsAsync(
        TaskGraph plan,
        ExecutionOptions options,
        IProgress<ExecutionProgress>? progress,
        CancellationToken ct)
    {
        var planner = new TaskPlanner(_logger as ILogger<TaskPlanner> ?? LoggerFactory.Create(b => b.AddConsole()).CreateLogger<TaskPlanner>());
        
        // 获取依赖分析
        var analysis = await planner.AnalyzeDependenciesAsync(plan.Id, ct);
        
        var completedCount = 0;
        var totalCount = plan.Nodes.Count;
        
        // 按层级执行
        foreach (var (level, taskIds) in analysis.Levels.OrderBy(l => l.Key))
        {
            ct.ThrowIfCancellationRequested();
            
            progress?.Report(new ExecutionProgress(
                $"执行层级 {level + 1}/{analysis.Levels.Count}...",
                (double)completedCount / totalCount * 100
            ));
            
            // 获取该层级的任务
            var levelTasks = taskIds
                .Where(id => plan.Nodes.TryGetValue(id, out var node) && node.Status == TaskStatus.Pending)
                .Select(id => plan.Nodes[id])
                .ToList();
            
            // 并行获取SubAgent
            var agents = new List<ISubAgent>();
            foreach (var task in levelTasks)
            {
                var agent = await _subAgentPool.AcquireAsync(ct);
                agents.Add(agent);
            }
            
            // 创建SubAgent任务
            var subAgentTasks = levelTasks.Zip(agents, (task, agent) => new SubAgentTask
            {
                Name = task.Name,
                Description = task.Description,
                Input = task.Description,
                Type = task.SubAgentType switch
                {
                    SubAgentType.Coder => core.TaskType.CodeGeneration,
                    SubAgentType.Tester => core.TaskType.Testing,
                    SubAgentType.Reviewer => core.TaskType.CodeReview,
                    SubAgentType.Researcher => core.TaskType.Search,
                    _ => core.TaskType.General
                },
                AssignedAgentId = agent.Id
            }).ToList();
            
            // 并行执行
            async Task<(bool Success, SubAgentTask Task, string? Error)> ExecuteWithReleaseAsync(
                SubAgentTask subTask, subagent.ISubAgent agent)
            {
                try
                {
                    var response = await agent.ExecuteAsync(subTask, ct);
                    return (response.Success, subTask, response.Error);
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "SubAgent {AgentId} failed on task {TaskId}", agent.Id, subTask.Id);
                    return (false, subTask, ex.Message);
                }
                finally
                {
                    await _subAgentPool.ReleaseAsync(agent);
                }
            }

            var executionTasks = subAgentTasks.Zip(agents,
                (subTask, agent) => ExecuteWithReleaseAsync(subTask, agent));
            
            var results = await Task.WhenAll(executionTasks);
            
            // 处理结果
            foreach (var result in results)
            {
                if (!result.Success)
                {
                    // 创建错误确认交互点
                    var errorInteraction = await _interactionManager.CreateInteractionAsync(
                        taskId: plan.RootTaskId,
                        type: InteractionPointType.ErrorConfirmation,
                        title: "任务执行出错",
                        message: $"任务 \"{result.Task.Name}\" 执行失败:\n\n{result.Error}",
                        options: new List<InteractionOption>
                        {
                            new() { Id = "retry", Label = "重试", IsRecommended = true },
                            new() { Id = "skip", Label = "跳过" },
                            new() { Id = "abort", Label = "终止", IsDestructive = true }
                        },
                        isRequired: true
                    );
                    
                    var errorResponse = await _interactionManager.WaitForResponseAsync(errorInteraction.Id, ct);
                    
                    // 存储错误反馈
                    await _feedbackStore.StoreAsync(new UserFeedback
                    {
                        TaskId = plan.RootTaskId,
                        InteractionId = errorInteraction.Id,
                        SelectedOptionId = errorResponse?.SelectedOptionId ?? "timeout",
                        UserComment = errorResponse?.UserComment,
                        TaskDescription = result.Task.Name,
                        Context = result.Error ?? "Unknown error"
                    });
                    
                    if (errorResponse?.SelectedOptionId == "abort")
                    {
                        throw new OperationCanceledException($"Task aborted by user: {result.Task.Name}");
                    }
                }
                
                completedCount++;
                progress?.Report(new ExecutionProgress(
                    $"已完成: {result.Task.Name}",
                    (double)completedCount / totalCount * 100
                ));
            }
        }
    }
    
    /// <summary>
    /// 确认结果
    /// </summary>
    private async Task<bool> ConfirmResultAsync(TaskGraph plan, ExecutionOptions options, CancellationToken ct)
    {
        var interaction = await _interactionManager.CreateInteractionAsync(
            taskId: plan.RootTaskId,
            type: InteractionPointType.ResultConfirmation,
            title: "任务完成",
            message: $"任务已完成:\n\n{plan.Name}\n\n共执行 {plan.Nodes.Count} 个步骤",
            options: new List<InteractionOption>
            {
                new() { Id = "approve", Label = "确认完成", IsRecommended = true },
                new() { Id = "revise", Label = "需要修改" },
                new() { Id = "save", Label = "保存并完成" }
            },
            isRequired: true
        );
        
        var response = await _interactionManager.WaitForResponseAsync(interaction.Id, ct);
        
        await _feedbackStore.StoreAsync(new UserFeedback
        {
            TaskId = plan.RootTaskId,
            InteractionId = interaction.Id,
            SelectedOptionId = response?.SelectedOptionId ?? "timeout",
            SelectedOptionLabel = response?.Options.FirstOrDefault(o => o.Id == response?.SelectedOptionId)?.Label,
            UserComment = response?.UserComment,
            TaskDescription = plan.Name,
            Context = plan.Name,
            Outcome = response?.SelectedOptionId == "approve" ? "Approved" : "Needs revision"
        });
        
        return response?.SelectedOptionId == "approve" || response?.SelectedOptionId == "save";
    }
    
    /// <summary>
    /// 保存反馈到RAG
    /// </summary>
    private async Task SaveFeedbackAsync(TaskGraph plan, TaskExecutionResult result, CancellationToken ct)
    {
        var feedback = new UserFeedback
        {
            TaskId = plan.RootTaskId,
            TaskDescription = plan.Name,
            Context = plan.Name,
            Outcome = result.Status.ToString(),
            Keywords = DecomposeIntoSubTasks(plan.Name).Select(t => t.Name).ToList()
        };
        
        await _feedbackStore.StoreAsync(feedback);
        
        _logger.LogInformation("Feedback saved to RAG for task {TaskId}", plan.RootTaskId);
    }
}

/// <summary>
/// SubAgent类型
/// </summary>
public enum SubAgentType
{
    Coder,
    Tester,
    Reviewer,
    Researcher,
    Planner
}

/// <summary>
/// 执行选项
/// </summary>
public class ExecutionOptions
{
    public bool RequireConfirmation { get; set; } = true;
    public bool AutoSaveToRAG { get; set; } = true;
    public int MaxParallelAgents { get; set; } = 4;
    public TimeSpan TaskTimeout { get; set; } = TimeSpan.FromMinutes(10);
    public bool EnableRecovery { get; set; } = true;
    public List<InteractionPointType> RequiredInteractionPoints { get; set; } = new()
    {
        InteractionPointType.TaskConfirmation,
        InteractionPointType.ResultConfirmation
    };
}

/// <summary>
/// 执行进度
/// </summary>
public class ExecutionProgress
{
    public string Status { get; set; }
    public double PercentComplete { get; set; }
    public string? CurrentTask { get; set; }
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    
    public ExecutionProgress(string status, double percentComplete, string? currentTask = null)
    {
        Status = status;
        PercentComplete = percentComplete;
        CurrentTask = currentTask;
    }
}

/// <summary>
/// 执行结果
/// </summary>
public class TaskExecutionResult
{
    public string TaskDescription { get; set; } = string.Empty;
    public string? PlanId { get; set; }
    public ExecutionStatus Status { get; set; }
    public string? Error { get; set; }
    public string? AbortReason { get; set; }
    public List<RecoveryAction>? RecoveryOptions { get; set; }
    public DateTime StartedAt { get; set; } = DateTime.UtcNow;
    public DateTime? CompletedAt { get; set; }
    public TimeSpan Duration => CompletedAt.HasValue ? CompletedAt.Value - StartedAt : TimeSpan.Zero;
}

/// <summary>
/// 执行状态
/// </summary>
public enum ExecutionStatus
{
    Created,
    InProgress,
    Completed,
    NeedsRevision,
    Aborted,
    Failed
}
