using System.Text.Json.Serialization;

namespace agent.llamacpp;


internal sealed class TokenizeRequest
{
    [JsonPropertyName("content")] public string Content { get; set; } = string.Empty;
    [JsonPropertyName("add_special")] public bool AddSpecial { get; set; } = true;
}
