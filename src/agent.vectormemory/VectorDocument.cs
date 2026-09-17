using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.vectormemory;

/// <summary>
/// 记忆条目
/// </summary>
public class VectorDocument
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Content { get; set; } = string.Empty;
    public string? Summary { get; set; }
    public float[]? Embedding { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime LastAccessedAt { get; set; } = DateTime.UtcNow;
    public int AccessCount { get; set; }
    public List<string> Keywords { get; set; } = new();
    public Dictionary<string, object> Metadata { get; set; } = new();
    public double RelevanceScore { get; set; }
}
