using System.Text.Json.Serialization;

namespace agent.llamacpp;


internal sealed class EmbeddingRequest
{
    [JsonPropertyName("input")] public string[] Input { get; set; } = [];
    [JsonPropertyName("model")] public string Model { get; set; } = "local";
    [JsonPropertyName("encoding_format")] public string EncodingFormat { get; set; } = "float";
}
