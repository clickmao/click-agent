using System.Text.Json.Serialization;

namespace agent.llamacpp;


internal sealed class TokenizeResponse
{
    [JsonPropertyName("tokens")] public int[]? Tokens { get; set; }
}
