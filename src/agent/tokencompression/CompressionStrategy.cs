using Microsoft.Extensions.Logging;
using System.Text.RegularExpressions;

namespace agent.tokencompression;


/// <summary>
/// 压缩策略
/// </summary>
public enum CompressionStrategy
{
    /// <summary>总结摘要：保留首尾</summary>
    Summarize,
    
    /// <summary>截断：简单切除</summary>
    Truncate,
    
    /// <summary>选择性保留：保留关键词周围内容</summary>
    Selective,
    
    /// <summary>智能压缩：分析语义保留核心</summary>
    Smart,
    
    /// <summary>增量压缩：渐进式压缩</summary>
    Incremental
}
