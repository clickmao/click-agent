using Microsoft.Extensions.Logging;

namespace agent.memory;


/// <summary>
/// 记忆存储接口
/// </summary>
public class SummarizeOptions
{
    /// <summary>
    /// 最大Token数
    /// </summary>
    public int MaxTokens { get; set; } = 500;
    
    /// <summary>
    /// 是否提取关键事实
    /// </summary>
    public bool ExtractKeyFacts { get; set; } = true;
    
    /// <summary>
    /// 是否提取决策
    /// </summary>
    public bool ExtractDecisions { get; set; } = true;
    
    /// <summary>
    /// 压缩比例
    /// </summary>
    public double CompressionRatio { get; set; } = 0.3;
}
