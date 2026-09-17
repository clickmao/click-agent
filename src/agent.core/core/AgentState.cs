namespace agent.core;


/// <summary>
/// Agent状态枚举
/// </summary>
public enum AgentState
{
    /// <summary>初始状态</summary>
    Initial,
    
    /// <summary>初始化中</summary>
    Initializing,
    
    /// <summary>就绪</summary>
    Ready,
    
    /// <summary>处理中</summary>
    Processing,
    
    /// <summary>等待用户输入</summary>
    WaitingForInput,
    
    /// <summary>暂停</summary>
    Paused,
    
    /// <summary>错误</summary>
    Error,
    
    /// <summary>已关闭</summary>
    Shutdown
}
