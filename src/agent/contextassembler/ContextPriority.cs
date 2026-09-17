using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


/// <summary>
/// 上下文优先级
/// </summary>
public enum ContextPriority
{
    /// <summary>低优先级</summary>
    Low = 0,
    
    /// <summary>普通优先级</summary>
    Normal = 1,
    
    /// <summary>高优先级</summary>
    High = 2,
    
    /// <summary>关键优先级（不可压缩）</summary>
    Critical = 3
}
