using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.vectormemory;


/// <summary>
/// 语义搜索结果
/// </summary>
public class SemanticSearchResult
{
    public VectorDocument Entry { get; set; } = null!;
    public double Score { get; set; }
    public string? HighlightedContent { get; set; }
    public int Rank { get; set; }
}
