using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.rag;


/// <summary>
/// 召回请求
/// </summary>
public class RecallRequest
{
    public string Query { get; set; } = string.Empty;
    public string? SessionId { get; set; }
    public string? UserId { get; set; }
    public string? DocumentType { get; set; }
    public int TopK { get; set; } = 5;
    public double? MinScore { get; set; }
    public List<string>? FilterKeywords { get; set; }
    public DateTime? FromDate { get; set; }
    public DateTime? ToDate { get; set; }
    public bool IncludeMetadata { get; set; } = true;
}
