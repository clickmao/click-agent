using System.Text.Json.Serialization;

namespace agent.llamacpp;


internal sealed class EmbeddingData
{
    [JsonPropertyName("index")] public int Index { get; set; }
    [JsonPropertyName("embedding")] public float[] Embedding { get; set; } = [];
}
