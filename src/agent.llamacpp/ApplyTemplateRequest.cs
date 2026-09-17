using System.Text.Json.Serialization;

namespace agent.llamacpp;


internal sealed class ApplyTemplateRequest
{
    [JsonPropertyName("messages")] public TemplateMessage[] Messages { get; set; } = [];
    [JsonPropertyName("add_generation_prompt")] public bool AddGenerationPrompt { get; set; } = true;
}
