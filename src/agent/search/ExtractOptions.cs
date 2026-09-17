namespace agent.search;


/// <summary>
/// 内容提取选项
/// </summary>
public class ExtractOptions
{
    /// <summary>
    /// 最大长度
    /// </summary>
    public int MaxLength { get; set; } = 50000;
    
    /// <summary>
    /// 是否提取元数据
    /// </summary>
    public bool ExtractMetadata { get; set; } = true;
    
    /// <summary>
    /// 是否清理HTML
    /// </summary>
    public bool CleanHtml { get; set; } = true;
    
    /// <summary>
    /// 超时时间（秒）
    /// </summary>
    public int TimeoutSeconds { get; set; } = 30;
}
