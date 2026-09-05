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

/// <summary>
/// 搜索来源
/// </summary>
public enum SearchResultSource
{
    /// <summary>搜索插件 (博查/SearXNG/DDG/BingCN/百度等)</summary>
    Provider,
    
    /// <summary>缓存</summary>
    Cache,
    
    /// <summary>记忆</summary>
    Memory,
    
    /// <summary>WebReaper CLI 抓取</summary>
    WebReaper
}

/// <summary>
/// 搜索选项
/// </summary>
public class SearchOptions
{
    /// <summary>
    /// 最大结果数
    /// </summary>
    public int MaxResults { get; set; } = 10;
    
    /// <summary>
    /// 语言
    /// </summary>
    public string? Language { get; set; }
    
    /// <summary>
    /// 开始日期
    /// </summary>
    public DateTime? FromDate { get; set; }
    
    /// <summary>
    /// 结束日期
    /// </summary>
    public DateTime? ToDate { get; set; }
    
    /// <summary>
    /// 文件类型
    /// </summary>
    public string? FileType { get; set; }
    
    /// <summary>
    /// 站点
    /// </summary>
    public string? Site { get; set; }
    
    /// <summary>
    /// 是否提取内容
    /// </summary>
    public bool ExtractContent { get; set; } = false;
    
    /// <summary>
    /// 排序方式
    /// </summary>
    public SearchSortBy SortBy { get; set; } = SearchSortBy.Relevance;
}

/// <summary>
/// 排序方式
/// </summary>
public enum SearchSortBy
{
    /// <summary>相关性</summary>
    Relevance,
    
    /// <summary>日期</summary>
    Date,
    
    /// <summary>标题</summary>
    Title
}

/// <summary>
/// 批量搜索选项
/// </summary>
public class BatchSearchOptions
{
    /// <summary>
    /// 并发数
    /// </summary>
    public int MaxConcurrency { get; set; } = 3;
    
    /// <summary>
    /// 默认搜索选项
    /// </summary>
    public SearchOptions? DefaultOptions { get; set; }
}

/// <summary>
/// 内容提取选项
/// </summary>
public class ExtractOptions
{
    /// <summary>
    /// 最大长度
    /// </summary>
    public int MaxLength { get; set; } = 50000;
    
    /// <summary>
    /// 是否提取元数据
    /// </summary>
    public bool ExtractMetadata { get; set; } = true;
    
    /// <summary>
    /// 是否清理HTML
    /// </summary>
    public bool CleanHtml { get; set; } = true;
    
    /// <summary>
    /// 超时时间（秒）
    /// </summary>
    public int TimeoutSeconds { get; set; } = 30;
}

/// <summary>
/// 搜索服务接口
/// </summary>
public interface ISearchService
{
    /// <summary>
    /// 搜索
    /// </summary>
    Task<SearchResult> SearchAsync(string query, SearchOptions? options = null, CancellationToken ct = default);
    
    /// <summary>
    /// 批量搜索
    /// </summary>
    Task<IEnumerable<SearchResult>> BatchSearchAsync(
        IEnumerable<string> queries, 
        BatchSearchOptions? options = null, 
        CancellationToken ct = default);
    
    /// <summary>
    /// 提取页面内容
    /// </summary>
    Task<string> ExtractContentAsync(string url, ExtractOptions? options = null, CancellationToken ct = default);
    
    /// <summary>
    /// 获取缓存的搜索结果
    /// </summary>
    Task<IEnumerable<SearchResult>> GetCachedResultsAsync(string query);
    
    /// <summary>
    /// 清除缓存
    /// </summary>
    Task ClearCacheAsync();
}
