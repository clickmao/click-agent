using agent.core;

namespace agent.context;


/// <summary>
/// 静态扩展方法
/// </summary>
public static class ContextSnippetExtensions
{
    /// <summary>
    /// 从 Message 创建片段
    /// </summary>
    public static ContextSnippet FromMessage(Message message, double relevanceScore = 0.5)
    {
        return new ContextSnippet
        {
            SourceType = DataSourceType.Session,
            SourceName = "Session",
            Content = $"[{message.Role}] {message.Content}",
            RelevanceScore = relevanceScore,
            CreatedAt = message.Timestamp,
            Metadata = new Dictionary<string, object>
            {
                { "messageId", message.Id },
                { "role", message.Role.ToString() }
            },
            EstimatedTokens = EstimateTokens(message.Content),
            Tags = new List<string> { message.Role.ToString().ToLower() }
        };
    }
    
    /// <summary>
    /// 从 RAG 结果创建片段
    /// </summary>
    public static ContextSnippet FromRAGResult(
        rag.RecallResult result, 
        string sourceName = "RAG Memory")
    {
        return new ContextSnippet
        {
            Id = result.Document.Id,
            SourceType = DataSourceType.Memory,
            SourceName = sourceName,
            Content = result.HighlightedContent ?? result.Document.Content,
            RelevanceScore = result.Score,
            CreatedAt = result.Document.CreatedAt,
            Metadata = result.Document.Metadata,
            Tags = result.Document.Keywords,
            EstimatedTokens = EstimateTokens(result.Document.Content)
        };
    }
    
    /// <summary>
    /// 估算 Token
    /// </summary>
    public static int EstimateTokens(string text)
    {
        if (string.IsNullOrEmpty(text)) return 0;
        
        var chineseChars = text.Count(c => c >= 0x4E00 && c <= 0x9FFF);
        var englishWords = text.Split(' ', StringSplitOptions.RemoveEmptyEntries).Length;
        
        return (int)(chineseChars * 1.5 + englishWords * 1.3);
    }
}
