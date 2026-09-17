using Microsoft.Extensions.Logging;
using System.Text.RegularExpressions;

namespace agent.tokencompression;


/// <summary>
/// 压缩选项
/// </summary>
public class CompressionOptions
{
    /// <summary>
    /// 最大Token数
    /// </summary>
    public int MaxTokens { get; set; } = 500;
    
    /// <summary>
    /// 压缩策略
    /// </summary>
    public CompressionStrategy Strategy { get; set; } = CompressionStrategy.Selective;
    
    /// <summary>
    /// 保留结构（如代码缩进、列表）
    /// </summary>
    public bool PreserveStructure { get; set; } = true;
    
    /// <summary>
    /// 保留关键词
    /// </summary>
    public bool PreserveKeywords { get; set; } = true;
    
    /// <summary>
    /// 保留行号
    /// </summary>
    public bool PreserveLineNumbers { get; set; } = false;
    
    /// <summary>
    /// 保留注释
    /// </summary>
    public bool PreserveComments { get; set; } = false;
    
    /// <summary>
    /// 压缩比 (0.0-1.0)
    /// </summary>
    public double CompressionRatio { get; set; } = 0.5;
    
    /// <summary>
    /// 关键词列表（优先保留）
    /// </summary>
    public List<string>? PriorityKeywords { get; set; }
}
