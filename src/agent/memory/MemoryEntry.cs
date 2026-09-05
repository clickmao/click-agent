namespace agent.memory;

/// <summary>
/// 记忆条目模型
/// </summary>
public class MemoryEntry
{
    /// <summary>
    /// 唯一标识
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 记忆内容
    /// </summary>
    public string Content { get; init; } = string.Empty;
    
    /// <summary>
    /// 记忆类型
    /// </summary>
    public MemoryType MemoryType { get; set; } = MemoryType.ShortTerm;
    
    /// <summary>
    /// 关联的会话ID
    /// </summary>
    public string SessionId { get; init; } = string.Empty;
    
    /// <summary>
    /// 创建时间
    /// </summary>
    public DateTime CreatedAt { get; init; } = DateTime.UtcNow;
    
    /// <summary>
    /// 更新时间
    /// </summary>
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// 过期时间
    /// </summary>
    public DateTime? ExpiresAt { get; set; }
    
    /// <summary>
    /// 重要性评分（0-10）
    /// </summary>
    public double Importance { get; set; } = 5.0;
    
    /// <summary>
    /// 标签列表
    /// </summary>
    public ISet<string> Tags { get; init; } = new HashSet<string>();
    
    /// <summary>
    /// Token数量估计
    /// </summary>
    public int TokenCount { get; set; }
    
    /// <summary>
    /// 关联的上下文引用
    /// </summary>
    public IReadOnlyList<string> ContextReferences { get; init; } = Array.Empty<string>();
    
    /// <summary>
    /// 记忆来源
    /// </summary>
    public string? Source { get; init; }
    
    /// <summary>
    /// 摘要（如果记忆被压缩）
    /// </summary>
    public string? Summary { get; set; }
    
    /// <summary>
    /// 访问计数
    /// </summary>
    public int AccessCount { get; set; }
    
    /// <summary>
    /// 最后访问时间
    /// </summary>
    public DateTime LastAccessedAt { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// 创建新的记忆条目
    /// </summary>
    public static MemoryEntry Create(string content, string sessionId, string? source = null)
    {
        return new MemoryEntry
        {
            Content = content,
            SessionId = sessionId,
            Source = source,
            TokenCount = EstimateTokens(content)
        };
    }
    
    /// <summary>
    /// 简单估计Token数量（约4个字符=1个Token）
    /// </summary>
    public static int EstimateTokens(string text)
    {
        return string.IsNullOrEmpty(text) ? 0 : (int)Math.Ceiling(text.Length / 4.0);
    }
}

/// <summary>
/// 记忆类型枚举
/// </summary>
public enum MemoryType
{
    /// <summary>
    /// 短期记忆
    /// </summary>
    ShortTerm,
    
    /// <summary>
    /// 长期记忆
    /// </summary>
    LongTerm,
    
    /// <summary>
    /// 工作记忆
    /// </summary>
    Working,
    
    /// <summary>
    /// 情节记忆
    /// </summary>
    Episodic,
    
    /// <summary>
    /// 语义记忆
    /// </summary>
    Semantic
}
