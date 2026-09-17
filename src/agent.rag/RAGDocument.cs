using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.rag;


/// <summary>
/// RAG文档
/// </summary>
public class RAGDocument
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Content { get; set; } = string.Empty;
    public string? Summary { get; set; }
    public float[]? Embedding { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    public List<string> Keywords { get; set; } = new();
    public string DocumentType { get; set; } = "general";
    public Dictionary<string, object> Metadata { get; set; } = new();
    public double? RelevanceScore { get; set; }
    public int AccessCount { get; set; }
    public DateTime LastAccessedAt { get; set; } = DateTime.UtcNow;
}
