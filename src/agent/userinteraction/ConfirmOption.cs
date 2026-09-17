namespace agent.userinteraction;


/// <summary>
/// 确认选项
/// </summary>
public class ConfirmOption
{
    /// <summary>
    /// 选项ID
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 标签
    /// </summary>
    public string Label { get; set; } = string.Empty;
    
    /// <summary>
    /// 描述
    /// </summary>
    public string? Description { get; set; }
    
    /// <summary>
    /// 是否推荐
    /// </summary>
    public bool IsRecommended { get; set; }
    
    /// <summary>
    /// 元数据
    /// </summary>
    public Dictionary<string, object> Metadata { get; set; } = new();
}
