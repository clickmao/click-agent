namespace agent.core;


/// <summary>
/// Agent状态变更事件参数
/// </summary>
public class AgentStateChangedEventArgs : EventArgs
{
    /// <summary>
    /// Agent ID
    /// </summary>
    public string AgentId { get; set; } = string.Empty;
    
    /// <summary>
    /// 旧状态
    /// </summary>
    public AgentState OldState { get; set; }
    
    /// <summary>
    /// 新状态
    /// </summary>
    public AgentState NewState { get; set; }
    
    /// <summary>
    /// 变更原因
    /// </summary>
    public string? Reason { get; set; }
}
