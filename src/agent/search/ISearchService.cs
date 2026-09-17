namespace agent.search;


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
