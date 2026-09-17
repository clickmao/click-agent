using System.Text.Json.Serialization;

namespace agent.llamacpp;


internal sealed class HealthResponse
{
    [JsonPropertyName("status")] public string? Status { get; set; }
}
