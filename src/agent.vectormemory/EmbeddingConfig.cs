using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.vectormemory;


/// <summary>
/// Embedding配置
/// </summary>
public class EmbeddingConfig
{
    public int Dimension { get; set; } = 384;
    public string ModelName { get; set; } = "default";
    public string? Endpoint { get; set; }
    public string? ApiKey { get; set; }
    public int MaxTokens { get; set; } = 512;
}
