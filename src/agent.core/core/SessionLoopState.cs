namespace agent.core;


/// <summary>
/// 会话循环状态
/// </summary>
public enum SessionLoopState
{
    /// <summary>已停止</summary>
    Stopped,
    
    /// <summary>运行中</summary>
    Running,
    
    /// <summary>暂停</summary>
    Paused,
    
    /// <summary>等待输入</summary>
    WaitingForInput,
    
    /// <summary>处理中</summary>
    Processing
}
