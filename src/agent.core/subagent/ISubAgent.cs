using agent.core;
using TaskStatus = agent.core.TaskStatus;

namespace agent.subagent;


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
