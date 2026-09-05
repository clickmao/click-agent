using agent.core;
using TaskStatus = agent.core.TaskStatus;

namespace agent.subagent;

/// <summary>
/// SubAgent任务模型
/// </summary>
public class SubAgentTask
{
    /// <summary>
    /// 任务ID
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 任务名称
    /// </summary>
    public string Name { get; set; } = string.Empty;
    
    /// <summary>
    /// 任务描述
    /// </summary>
    public string Description { get; set; } = string.Empty;
    
    /// <summary>
    /// 输入数据
    /// </summary>
    public string Input { get; set; } = string.Empty;
    
    /// <summary>
    /// 任务类型
    /// </summary>
    public TaskType Type { get; set; } = TaskType.General;
    
    /// <summary>
    /// 任务状态
    /// </summary>
    public TaskStatus Status { get; set; } = TaskStatus.Pending;
    
    /// <summary>
    /// 任务边界
    /// </summary>
    public TaskBoundary Boundary { get; set; } = new();
    
    /// <summary>
    /// 依赖的任务ID列表
    /// </summary>
    public List<string> Dependencies { get; set; } = new();
    
    /// <summary>
    /// 分配到的Agent ID
    /// </summary>
    public string? AssignedAgentId { get; set; }
    
    /// <summary>
    /// 创建时间
    /// </summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// 开始时间
    /// </summary>
    public DateTime? StartedAt { get; set; }
    
    /// <summary>
    /// 完成时间
    /// </summary>
    public DateTime? CompletedAt { get; set; }
    
    /// <summary>
    /// 超时时间（毫秒）
    /// </summary>
    public long TimeoutMs { get; set; } = 300000; // 5分钟
    
    /// <summary>
    /// Token预算
    /// </summary>
    public long TokenBudget { get; set; } = 8000;
    
    /// <summary>
    /// 执行结果
    /// </summary>
    public string? Result { get; set; }
    
    /// <summary>
    /// 错误信息
    /// </summary>
    public string? Error { get; set; }
    
    /// <summary>
    /// 进度（0-100）
    /// </summary>
    public double Progress { get; set; }
    
    /// <summary>
    /// 元数据
    /// </summary>
    public Dictionary<string, object> Metadata { get; set; } = new();
    
    /// <summary>
    /// 执行耗时（毫秒）
    /// </summary>
    public long ExecutionTimeMs => CompletedAt.HasValue && StartedAt.HasValue
        ? (long)(CompletedAt.Value - StartedAt.Value).TotalMilliseconds
        : 0;
}

/// <summary>
/// 任务边界定义
/// </summary>
public class TaskBoundary
{
    /// <summary>
    /// 任务ID
    /// </summary>
    public string TaskId { get; set; } = string.Empty;
    
    /// <summary>
    /// 输入需求
    /// </summary>
    public List<string> InputRequirements { get; set; } = new();
    
    /// <summary>
    /// 依赖
    /// </summary>
    public List<string> Dependencies { get; set; } = new();
    
    /// <summary>
    /// 输出文件
    /// </summary>
    public List<string> OutputFiles { get; set; } = new();
    
    /// <summary>
    /// 输出模式
    /// </summary>
    public List<string> OutputPatterns { get; set; } = new();
    
    /// <summary>
    /// 最大Token数
    /// </summary>
    public long MaxTokens { get; set; } = 8000;
    
    /// <summary>
    /// 超时时间（毫秒）
    /// </summary>
    public long TimeoutMs { get; set; } = 300000;
    
    /// <summary>
    /// 约束条件
    /// </summary>
    public Dictionary<string, object> Constraints { get; set; } = new();
    
    /// <summary>
    /// 上下文提示
    /// </summary>
    public Dictionary<string, object> ContextHints { get; set; } = new();
}

/// <summary>
/// SubAgent接口
/// </summary>
public interface ISubAgent
{
    /// <summary>
    /// Agent ID
    /// </summary>
    string Id { get; }
    
    /// <summary>
    /// Agent名称
    /// </summary>
    string Name { get; }
    
    /// <summary>
    /// 是否忙碌
    /// </summary>
    bool IsBusy { get; }
    
    /// <summary>
    /// 当前任务
    /// </summary>
    SubAgentTask? CurrentTask { get; }
    
    /// <summary>
    /// 初始化
    /// </summary>
    Task InitializeAsync(IAgentContext context, CancellationToken ct = default);
    
    /// <summary>
    /// 执行任务
    /// </summary>
    Task<AgentResponse> ExecuteAsync(SubAgentTask task, CancellationToken ct = default);
    
    /// <summary>
    /// 报告进度
    /// </summary>
    Task ReportProgressAsync(double progress, string? status = null);
    
    /// <summary>
    /// 取消任务
    /// </summary>
    Task CancelAsync();
}

/// <summary>
/// SubAgent池接口
/// </summary>
public interface ISubAgentPool
{
    /// <summary>
    /// 最大Agent数
    /// </summary>
    int MaxAgents { get; set; }
    
    /// <summary>
    /// 当前活跃Agent数
    /// </summary>
    int ActiveAgentCount { get; }
    
    /// <summary>
    /// 获取可用Agent
    /// </summary>
    Task<ISubAgent> AcquireAsync(CancellationToken ct = default);
    
    /// <summary>
    /// 释放Agent
    /// </summary>
    Task ReleaseAsync(ISubAgent agent);
    
    /// <summary>
    /// 尝试路由消息到Agent
    /// </summary>
    Task<bool> TryRouteAsync(Message message, out ISubAgent agent);
    
    /// <summary>
    /// 获取所有Agent
    /// </summary>
    IEnumerable<ISubAgent> GetAllAgents();
    
    /// <summary>
    /// 获取空闲Agent
    /// </summary>
    IEnumerable<ISubAgent> GetIdleAgents();
}
