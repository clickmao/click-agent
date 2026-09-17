using System.Text.Json.Serialization;

namespace agent.llamacpp;


internal sealed class EmbeddingResponse
{
    [JsonPropertyName("data")] public EmbeddingData[] Data { get; set; } = [];
}
