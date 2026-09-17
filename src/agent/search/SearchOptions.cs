namespace agent.search;


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
