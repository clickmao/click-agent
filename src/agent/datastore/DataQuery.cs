namespace agent.datastore;


/// <summary>
/// 数据查询
/// </summary>
public class DataQuery
{
    public string? Category { get; set; }
    public List<string>? Tags { get; set; }
    public string? KeyPattern { get; set; }
    public DateTime? FromDate { get; set; }
    public DateTime? ToDate { get; set; }
    public int Skip { get; set; }
    public int Take { get; set; } = 50;
}
