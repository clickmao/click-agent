namespace agent.core;


/// <summary>
/// 会话状态
/// </summary>
public enum SessionState
{
    /// <summary>初始</summary>
    Initial,
    
    /// <summary>活跃</summary>
    Active,
    
    /// <summary>暂停</summary>
    Paused,
    
    /// <summary>等待确认</summary>
    WaitingForConfirmation,
    
    /// <summary>已完成</summary>
    Completed,
    
    /// <summary>已终止</summary>
    Terminated
}
