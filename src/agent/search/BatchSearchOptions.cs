namespace agent.search;


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
