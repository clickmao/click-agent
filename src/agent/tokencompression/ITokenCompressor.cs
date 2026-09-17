using Microsoft.Extensions.Logging;
using System.Text.RegularExpressions;

namespace agent.tokencompression;

/// <summary>
/// Token压缩器接口
/// </summary>
public interface ITokenCompressor
{
    /// <summary>
    /// 压缩上下文
    /// </summary>
    Task<string> CompressAsync(string context, CompressionOptions? options = null);
    
    /// <summary>
    /// 计算Token数
    /// </summary>
    Task<int> CountTokensAsync(string text);
    
    /// <summary>
    /// 截断到指定Token数
    /// </summary>
    Task<string> TruncateAsync(string text, int maxTokens);
    
    /// <summary>
    /// 智能压缩（保留语义）
    /// </summary>
    Task<string> CompressSmartAsync(string context, int maxTokens);
}
