namespace agent.core;


/// <summary>
/// 消息角色
/// </summary>
public enum MessageRole
{
    /// <summary>系统消息</summary>
    System,
    
    /// <summary>用户消息</summary>
    User,
    
    /// <summary>助手消息</summary>
    Assistant,
    
    /// <summary>工具消息</summary>
    Tool,
    
    /// <summary>子Agent消息</summary>
    SubAgent
}
