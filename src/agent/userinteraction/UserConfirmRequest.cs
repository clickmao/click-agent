namespace agent.userinteraction;

/// <summary>
/// 用户确认请求
/// </summary>
public class UserConfirmRequest
{
    /// <summary>
    /// 请求ID
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 确认类型
    /// </summary>
    public core.ConfirmationType Type { get; set; }
    
    /// <summary>
    /// 消息
    /// </summary>
    public string Message { get; set; } = string.Empty;
    
    /// <summary>
    /// 详情
    /// </summary>
    public string? Details { get; set; }
    
    /// <summary>
    /// 选项列表
    /// </summary>
    public List<ConfirmOption> Options { get; set; } = new();
    
    /// <summary>
    /// 默认选项
    /// </summary>
    public string? DefaultOption { get; set; }
    
    /// <summary>
    /// 超时时间
    /// </summary>
    public TimeSpan? Timeout { get; set; }
    
    /// <summary>
    /// 上下文
    /// </summary>
    public Dictionary<string, object> Context { get; set; } = new();
}
