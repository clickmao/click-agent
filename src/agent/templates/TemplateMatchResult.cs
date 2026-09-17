namespace agent.templates;


/// <summary>
/// 模板匹配结果
/// </summary>
public class TemplateMatchResult
{
    /// <summary>
    /// 匹配的模板
    /// </summary>
    public Template Template { get; set; } = null!;
    
    /// <summary>
    /// 匹配分数
    /// </summary>
    public double Score { get; set; }
    
    /// <summary>
    /// 匹配的标签
    /// </summary>
    public List<string> MatchedTags { get; set; } = new();
    
    /// <summary>
    /// 匹配原因
    /// </summary>
    public string Reason { get; set; } = string.Empty;
    
    /// <summary>
    /// 是否推荐
    /// </summary>
    public bool IsRecommended => Score >= 0.7;
}
