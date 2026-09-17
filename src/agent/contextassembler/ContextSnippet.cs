using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;


/// <summary>
/// 上下文片段（来自不同数据源）
/// </summary>
public class ContextSnippet
{
    /// <summary>唯一标识</summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>数据源类型</summary>
    public DataSourceType SourceType { get; set; }
    
    /// <summary>数据源名称</summary>
    public string SourceName { get; set; } = string.Empty;
    
    /// <summary>原始内容</summary>
    public string Content { get; set; } = string.Empty;
    
    /// <summary>压缩后的内容</summary>
    public string? CompressedContent { get; set; }
    
    /// <summary>相关性得分 (0-1)</summary>
    public double RelevanceScore { get; set; }
    
    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    /// <summary>过期时间（可选）</summary>
    public DateTime? ExpiresAt { get; set; }
    
    /// <summary>是否已压缩</summary>
    public bool IsCompressed { get; set; }
    
    /// <summary>元数据</summary>
    public Dictionary<string, object> Metadata { get; set; } = new();
    
    /// <summary>Token数估算</summary>
    public int EstimatedTokens { get; set; }
    
    /// <summary>标签（用于分类/过滤）</summary>
    public List<string> Tags { get; set; } = new();
}
