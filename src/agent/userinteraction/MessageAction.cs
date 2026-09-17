namespace agent.userinteraction;


/// <summary>
/// 消息操作
/// </summary>
public class MessageAction
{
    /// <summary>
    /// 操作ID
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 标签
    /// </summary>
    public string Label { get; set; } = string.Empty;
    
    /// <summary>
    /// 操作类型
    /// </summary>
    public MessageActionType Type { get; set; } = MessageActionType.Button;
}
