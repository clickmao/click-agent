using agent.core;
using TaskStatus = agent.core.TaskStatus;

namespace agent.core;

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
