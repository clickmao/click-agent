namespace agent.search;

/// <summary>
/// 搜索结果模型
/// </summary>
public class SearchResult
{
    /// <summary>
    /// 结果ID
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();
    
    /// <summary>
    /// 搜索查询
    /// </summary>
    public string Query { get; set; } = string.Empty;
    
    /// <summary>
    /// 标题
    /// </summary>
    public string Title { get; set; } = string.Empty;
    
    /// <summary>
    /// URL
    /// </summary>
    public string Url { get; set; } = string.Empty;
    
    /// <summary>
    /// 摘要
    /// </summary>
    public string Snippet { get; set; } = string.Empty;
    
    /// <summary>
    /// 完整内容
    /// </summary>
    public string? Content { get; set; }
    
    /// <summary>
    /// 相关性分数
    /// </summary>
    public double RelevanceScore { get; set; }
    
    /// <summary>
    /// 爬取时间
    /// </summary>
    public DateTime CrawledAt { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// 关键词
    /// </summary>
    public List<string> Keywords { get; set; } = new();
    
    /// <summary>
    /// 来源
    /// </summary>
    public SearchResultSource Source { get; set; } = SearchResultSource.Provider;
    
    /// <summary>
    /// 元数据
    /// </summary>
    public Dictionary<string, object> Metadata { get; set; } = new();
}
