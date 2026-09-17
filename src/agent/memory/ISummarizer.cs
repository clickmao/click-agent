using Microsoft.Extensions.Logging;

namespace agent.memory;


/// <summary>
/// 摘要器接口
/// </summary>
public interface ISummarizer
{
    /// <summary>
    /// 生成摘要
    /// </summary>
    Task<string> SummarizeAsync(string content, SummarizeOptions? options = null);
    
    /// <summary>
    /// 提取关键事实
    /// </summary>
    Task<IEnumerable<string>> ExtractKeyFactsAsync(string content);
    
    /// <summary>
    /// 提取决策点
    /// </summary>
    Task<IEnumerable<string>> ExtractDecisionsAsync(string content);
}
