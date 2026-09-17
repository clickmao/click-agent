using System.Text.Json.Serialization;

namespace agent.llamacpp;


internal sealed class ApplyTemplateResponse
{
    [JsonPropertyName("prompt")] public string? Prompt { get; set; }
}
