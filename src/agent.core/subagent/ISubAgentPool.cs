using agent.core;
using TaskStatus = agent.core.TaskStatus;

namespace agent.subagent;


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
