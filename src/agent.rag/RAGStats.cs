using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.rag;


/// <summary>
/// RAG统计
/// </summary>
public class RAGStats
{
    public int TotalDocuments { get; set; }
    public int TotalKeywords { get; set; }
    public Dictionary<string, int> DocumentsByType { get; set; } = new();
    public DateTime OldestDocument { get; set; }
    public DateTime NewestDocument { get; set; }
}
