using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


/// <summary>
/// 上下文过期策略
/// </summary>
public class ContextExpirationPolicy
{
    /// <summary>
    /// 基于时间的过期
    /// </summary>
    public TimeSpan TimeToLive { get; set; } = TimeSpan.FromMinutes(30);
    
    /// <summary>
    /// 基于访问次数的过期
    /// </summary>
    public int MaxAccessCount { get; set; } = 100;
    
    /// <summary>
    /// 基于Token使用的过期
    /// </summary>
    public int MaxTokenUsage { get; set; } = 10000;
    
    /// <summary>
    /// 是否启用惰性删除
    /// </summary>
    public bool LazyDeletion { get; set; } = true;
}
