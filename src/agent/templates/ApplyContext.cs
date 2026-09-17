namespace agent.templates;


/// <summary>
/// 应用上下文
/// </summary>
public class ApplyContext
{
    /// <summary>
    /// 输入数据
    /// </summary>
    public Dictionary<string, object> Inputs { get; set; } = new();
    
    /// <summary>
    /// 配置选项
    /// </summary>
    public Dictionary<string, object> Options { get; set; } = new();
    
    /// <summary>
    /// 用户ID
    /// </summary>
    public string? UserId { get; set; }
    
    /// <summary>
    /// 会话ID
    /// </summary>
    public string? SessionId { get; set; }
}
