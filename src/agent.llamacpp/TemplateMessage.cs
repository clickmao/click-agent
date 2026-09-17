using System.Text.Json.Serialization;

namespace agent.llamacpp;


internal sealed class TemplateMessage
{
    [JsonPropertyName("role")] public string Role { get; set; } = "user";
    [JsonPropertyName("content")] public string Content { get; set; } = string.Empty;
}
