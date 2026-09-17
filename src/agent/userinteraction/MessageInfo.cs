namespace agent.userinteraction;


/// <summary>
/// 消息信息
/// </summary>
public class MessageInfo
{
    /// <summary>
    /// 消息类型
    /// </summary>
    public MessageInfoType Type { get; set; } = MessageInfoType.Info;
    
    /// <summary>
    /// 标题
    /// </summary>
    public string? Title { get; set; }
    
    /// <summary>
    /// 内容
    /// </summary>
    public string Content { get; set; } = string.Empty;
    
    /// <summary>
    /// 详情
    /// </summary>
    public string? Details { get; set; }
    
    /// <summary>
    /// 操作列表
    /// </summary>
    public List<MessageAction> Actions { get; set; } = new();
}
