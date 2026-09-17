using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


/// <summary>
/// 组装质量报告
/// </summary>
public class AssemblyQualityReport
{
    /// <summary>
    /// 总体质量
    /// </summary>
    public double OverallQuality { get; set; }
    
    /// <summary>
    /// 覆盖率
    /// </summary>
    public double Coverage { get; set; }
    
    /// <summary>
    /// 效率（Token使用率）
    /// </summary>
    public double Efficiency { get; set; }
    
    /// <summary>
    /// 多样性
    /// </summary>
    public double Diversity { get; set; }
    
    /// <summary>
    /// 各数据源质量
    /// </summary>
    public Dictionary<DataSourceType, double> QualityBySource { get; set; } = new();
    
    /// <summary>
    /// 问题
    /// </summary>
    public List<string> Issues { get; set; } = new();
    
    /// <summary>
    /// 优化建议
    /// </summary>
    public List<string> OptimizationSuggestions { get; set; } = new();
}
