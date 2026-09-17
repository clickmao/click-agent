namespace agent.templates;


/// <summary>
/// 模板匹配器接口
/// </summary>
public interface ITemplateMatcher
{
    /// <summary>
    /// 匹配模板
    /// </summary>
    Task<TemplateMatchResult?> MatchAsync(string input);
    
    /// <summary>
    /// 获取候选模板
    /// </summary>
    Task<IEnumerable<Template>> GetCandidatesAsync(string input, int topN = 5);
    
    /// <summary>
    /// 计算相似度
    /// </summary>
    Task<double> CalculateSimilarityAsync(string input, string templatePattern);
    
    /// <summary>
    /// 批量匹配
    /// </summary>
    Task<IEnumerable<TemplateMatchResult>> BatchMatchAsync(IEnumerable<string> inputs);
}
