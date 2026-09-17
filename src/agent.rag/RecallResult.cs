using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.rag;


/// <summary>
/// 召回结果
/// </summary>
public class RecallResult
{
    public RAGDocument Document { get; set; } = null!;
    public double Score { get; set; }
    public string? HighlightedContent { get; set; }
    public int Rank { get; set; }
    public string MatchType { get; set; } = "semantic"; // semantic, keyword, hybrid
}
