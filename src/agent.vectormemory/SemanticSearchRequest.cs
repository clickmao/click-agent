using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.vectormemory;


/// <summary>
/// 搜索请求
/// </summary>
public class SemanticSearchRequest
{
    public string Query { get; set; } = string.Empty;
    public int TopK { get; set; } = 5;
    public double? MinScore { get; set; }
    public List<string>? FilterKeywords { get; set; }
    public DateTime? FromDate { get; set; }
    public DateTime? ToDate { get; set; }
    public string? Category { get; set; }
}
