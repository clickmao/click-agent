using Microsoft.Extensions.Logging;

namespace agent.planner;

/// <summary>
/// 任务节点
/// </summary>
public class TaskNode
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public SubAgentType SubAgentType { get; set; } = SubAgentType.Coder;
    public TaskStatus Status { get; set; } = TaskStatus.Pending;
    public TaskPriority Priority { get; set; } = TaskPriority.Normal;
    public List<string> Dependencies { get; set; } = new();
    public List<string> Dependents { get; set; } = new();
    public int EstimatedMinutes { get; set; }
    public int ActualMinutes { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? StartedAt { get; set; }
    public DateTime? CompletedAt { get; set; }
    public string? Result { get; set; }
    public string? Error { get; set; }
    public Dictionary<string, object> Metadata { get; set; } = new();
    public List<TaskCheckpoint> Checkpoints { get; set; } = new();
}

/// <summary>
/// 任务状态
/// </summary>
public enum TaskStatus
{
    Pending,
    InProgress,
    WaitingForDependencies,
    Completed,
    Failed,
    Cancelled,
    Skipped
}

/// <summary>
/// 任务优先级
/// </summary>
public enum TaskPriority
{
    Low = 0,
    Normal = 1,
    High = 2,
    Critical = 3
}

/// <summary>
/// 任务检查点
/// </summary>
public class TaskCheckpoint
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Name { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public Dictionary<string, object> State { get; set; } = new();
    public bool IsMandatory { get; set; }
}

/// <summary>
/// 任务图
/// </summary>
public class TaskGraph
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Name { get; set; } = string.Empty;
    public string RootTaskId { get; set; } = string.Empty;
    public Dictionary<string, TaskNode> Nodes { get; set; } = new();
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? CompletedAt { get; set; }
    public PlanStatus Status { get; set; } = PlanStatus.Created;
    public double Progress => Nodes.Count > 0 ? (double)Nodes.Values.Count(n => n.Status == TaskStatus.Completed) / Nodes.Count * 100 : 0;
}

/// <summary>
/// 计划状态
/// </summary>
public enum PlanStatus
{
    Created,
    Analyzing,
    Ready,
    Executing,
    Paused,
    Completed,
    Failed,
    Cancelled
}

/// <summary>
/// 依赖分析结果
/// </summary>
public class DependencyAnalysis
{
    public List<string> RootTasks { get; set; } = new();
    public List<string> LeafTasks { get; set; } = new();
    public List<(string From, string To)> Edges { get; set; } = new();
    public Dictionary<int, List<string>> Levels { get; set; } = new(); // 层级深度 -> 任务ID列表
    public List<string> Cycles { get; set; } = new();
    public bool HasCycles => Cycles.Count > 0;
}

/// <summary>
/// 计划执行上下文
/// </summary>
public class ExecutionContext
{
    public string PlanId { get; set; } = string.Empty;
    public string CurrentTaskId { get; set; } = string.Empty;
    public int CurrentLevel { get; set; }
    public Dictionary<string, object> SharedState { get; set; } = new();
    public List<string> CompletedTaskIds { get; set; } = new();
    public List<string> FailedTaskIds { get; set; } = new();
    public DateTime StartTime { get; set; }
    public TimeSpan ElapsedTime => DateTime.UtcNow - StartTime;
}

/// <summary>
/// 执行结果
/// </summary>
public class ExecutionResult
{
    public bool Success { get; set; }
    public string? Error { get; set; }
    public List<TaskNode> CompletedTasks { get; set; } = new();
    public List<TaskNode> FailedTasks { get; set; } = new();
    public List<TaskNode> SkippedTasks { get; set; } = new();
    public TimeSpan Duration { get; set; }
    public Dictionary<string, object> Results { get; set; } = new();
}

/// <summary>
/// 任务规划器接口
/// </summary>
public interface ITaskPlanner
{
    /// <summary>
    /// 创建任务图
    /// </summary>
    Task<TaskGraph> CreatePlanAsync(string description, CancellationToken ct = default);
    
    /// <summary>
    /// 添加任务
    /// </summary>
    Task<TaskNode> AddTaskAsync(string planId, TaskNode task, CancellationToken ct = default);
    
    /// <summary>
    /// 分析依赖
    /// </summary>
    Task<DependencyAnalysis> AnalyzeDependenciesAsync(string planId, CancellationToken ct = default);
    
    /// <summary>
    /// 执行计划
    /// </summary>
    Task<ExecutionResult> ExecuteAsync(string planId, CancellationToken ct = default);
    
    /// <summary>
    /// 暂停计划
    /// </summary>
    Task PauseAsync(string planId, CancellationToken ct = default);
    
    /// <summary>
    /// 恢复计划
    /// </summary>
    Task ResumeAsync(string planId, CancellationToken ct = default);
    
    /// <summary>
    /// 取消计划
    /// </summary>
    Task CancelAsync(string planId, CancellationToken ct = default);
    
    /// <summary>
    /// 获取计划状态
    /// </summary>
    Task<TaskGraph?> GetPlanAsync(string planId, CancellationToken ct = default);
    
    /// <summary>
    /// 验证计划
    /// </summary>
    Task<PlanValidation> ValidateAsync(string planId, CancellationToken ct = default);
    
    /// <summary>
    /// 创建检查点
    /// </summary>
    Task CreateCheckpointAsync(string planId, string taskId, string checkpointName, CancellationToken ct = default);
    
    /// <summary>
    /// 恢复到检查点
    /// </summary>
    Task RecoveryAsync(string planId, string checkpointId, CancellationToken ct = default);
}

/// <summary>
/// 计划验证结果
/// </summary>
public class PlanValidation
{
    public bool IsValid { get; set; }
    public List<string> Errors { get; set; } = new();
    public List<string> Warnings { get; set; } = new();
    public List<string> Suggestions { get; set; } = new();
}
