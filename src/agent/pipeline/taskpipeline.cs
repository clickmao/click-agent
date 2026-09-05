namespace agent.pipeline;

/// <summary>
/// 管道任务
/// </summary>
public class PipelineTask
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Name { get; set; } = string.Empty;
    public string Input { get; set; } = string.Empty;
    public core.TaskType Type { get; set; } = core.TaskType.General;
    public core.TaskStatus Status { get; set; } = core.TaskStatus.Pending;
    public string? Result { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? StartedAt { get; set; }
    public DateTime? CompletedAt { get; set; }
    public double Progress { get; set; }
}

/// <summary>
/// 管道上下文
/// </summary>
public class PipelineContext
{
    public string SessionId { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public Dictionary<string, object> Data { get; set; } = new();
    public List<PipelineTask> Tasks { get; set; } = new();
    public Dictionary<string, string> Results { get; set; } = new();
}

/// <summary>
/// 任务管道接口
/// </summary>
public interface ITaskPipeline
{
    Task EnqueueAsync(PipelineTask task);
    Task<PipelineTask?> DequeueAsync(CancellationToken ct);
    Task CompleteAsync(string taskId, string result);
    Task FailAsync(string taskId, string error);
    IEnumerable<PipelineTask> GetPendingTasks();
    IEnumerable<PipelineTask> GetCompletedTasks();
}

/// <summary>
/// 任务管道实现
/// </summary>
public class TaskPipeline : ITaskPipeline
{
    private readonly Queue<PipelineTask> _queue = new();
    private readonly Dictionary<string, PipelineTask> _tasks = new();
    private readonly object _lock = new();
    
    public Task EnqueueAsync(PipelineTask task)
    {
        lock (_lock)
        {
            _queue.Enqueue(task);
            _tasks[task.Id] = task;
        }
        return Task.CompletedTask;
    }
    
    public Task<PipelineTask?> DequeueAsync(CancellationToken ct)
    {
        lock (_lock)
        {
            if (_queue.TryDequeue(out var task))
            {
                task.StartedAt = DateTime.UtcNow;
                task.Status = core.TaskStatus.Running;
                return Task.FromResult<PipelineTask?>(task);
            }
        }
        return Task.FromResult<PipelineTask?>(null);
    }
    
    public Task CompleteAsync(string taskId, string result)
    {
        lock (_lock)
        {
            if (_tasks.TryGetValue(taskId, out var task))
            {
                task.Status = core.TaskStatus.Completed;
                task.Result = result;
                task.CompletedAt = DateTime.UtcNow;
                task.Progress = 100;
            }
        }
        return Task.CompletedTask;
    }
    
    public Task FailAsync(string taskId, string error)
    {
        lock (_lock)
        {
            if (_tasks.TryGetValue(taskId, out var task))
            {
                task.Status = core.TaskStatus.Failed;
                task.CompletedAt = DateTime.UtcNow;
            }
        }
        return Task.CompletedTask;
    }
    
    public IEnumerable<PipelineTask> GetPendingTasks()
    {
        lock (_lock)
        {
            return _tasks.Values.Where(t => t.Status == core.TaskStatus.Pending).ToList();
        }
    }
    
    public IEnumerable<PipelineTask> GetCompletedTasks()
    {
        lock (_lock)
        {
            return _tasks.Values.Where(t => t.Status == core.TaskStatus.Completed).ToList();
        }
    }
}

/// <summary>
/// 任务分解结果
/// </summary>
public class DecompositionResult
{
    public List<subagent.SubAgentTask> Tasks { get; set; } = new();
    public Dictionary<string, List<string>> Dependencies { get; set; } = new();
    public long EstimatedTotalTokens { get; set; }
    public TimeSpan EstimatedDuration { get; set; }
}

/// <summary>
/// 分解选项
/// </summary>
public class DecomposeOptions
{
    public int MaxSubTasks { get; set; } = 10;
    public long MaxTokensPerTask { get; set; } = 8000;
    public bool ParallelExecution { get; set; } = true;
}

/// <summary>
/// 复杂度评估
/// </summary>
public class ComplexityAssessment
{
    public core.TaskType Type { get; set; }
    public int ComplexityLevel { get; set; } // 1-5
    public List<string> RequiredCapabilities { get; set; } = new();
    public long EstimatedTokens { get; set; }
    public TimeSpan EstimatedTime { get; set; }
    public List<string> Risks { get; set; } = new();
}

/// <summary>
/// 依赖图
/// </summary>
public class DependencyGraph
{
    public Dictionary<string, List<string>> Edges { get; set; } = new();
    public List<string> TopologicalOrder { get; set; } = new();
}

/// <summary>
/// 任务分解器接口
/// </summary>
public interface ITaskDecomposer
{
    Task<DecompositionResult> DecomposeAsync(string task, DecomposeOptions? options = null);
    Task<ComplexityAssessment> AssessComplexityAsync(string task);
    Task<DependencyGraph> AnalyzeDependenciesAsync(IEnumerable<string> tasks);
}

/// <summary>
/// 任务分解器实现
/// </summary>
public class TaskDecomposer : ITaskDecomposer
{
    public Task<DecompositionResult> DecomposeAsync(string task, DecomposeOptions? options = null)
    {
        options ??= new DecomposeOptions();
        
        var result = new DecompositionResult();
        
        // 简单的任务分解逻辑
        var subTasks = task.Split(new[] { '\n', ';', ',' }, StringSplitOptions.RemoveEmptyEntries);
        var tokenBudget = options.MaxTokensPerTask;
        
        foreach (var subTask in subTasks.Take(options.MaxSubTasks))
        {
            var subTaskObj = new subagent.SubAgentTask
            {
                Name = subTask.Trim(),
                Input = subTask.Trim(),
                Type = core.TaskType.General,
                TokenBudget = tokenBudget,
                TimeoutMs = 300000
            };
            result.Tasks.Add(subTaskObj);
        }
        
        result.EstimatedTotalTokens = result.Tasks.Count * tokenBudget;
        result.EstimatedDuration = TimeSpan.FromMinutes(result.Tasks.Count * 2);
        
        return Task.FromResult(result);
    }
    
    public Task<ComplexityAssessment> AssessComplexityAsync(string task)
    {
        var assessment = new ComplexityAssessment
        {
            Type = core.TaskType.General,
            ComplexityLevel = task.Length > 500 ? 4 : (task.Length > 200 ? 3 : 2),
            EstimatedTokens = task.Length * 2,
            EstimatedTime = TimeSpan.FromMinutes(task.Length > 500 ? 10 : 5)
        };
        
        return Task.FromResult(assessment);
    }
    
    public Task<DependencyGraph> AnalyzeDependenciesAsync(IEnumerable<string> tasks)
    {
        var graph = new DependencyGraph
        {
            TopologicalOrder = tasks.ToList()
        };
        
        return Task.FromResult(graph);
    }
}
