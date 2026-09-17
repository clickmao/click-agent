using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


/// <summary>
/// 上下文质量评分
/// </summary>
public class ContextQualityScore
{
    /// <summary>
    /// 总体质量分数 (0-1)
    /// </summary>
    public double OverallScore { get; set; }
    
    /// <summary>
    /// 相关性分数
    /// </summary>
    public double RelevanceScore { get; set; }
    
    /// <summary>
    /// 新鲜度分数
    /// </summary>
    public double FreshnessScore { get; set; }
    
    /// <summary>
    /// 完整性分数
    /// </summary>
    public double CompletenessScore { get; set; }
    
    /// <summary>
    /// 一致性分数
    /// </summary>
    public double ConsistencyScore { get; set; }
    
    /// <summary>
    /// 问题列表
    /// </summary>
    public List<string> Issues { get; set; } = new();
    
    /// <summary>
    /// 建议列表
    /// </summary>
    public List<string> Suggestions { get; set; } = new();
}
