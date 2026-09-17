using System.Text.Json.Serialization;

namespace agent.llamacpp;


internal sealed class PropsResponse
{
    [JsonPropertyName("bos_token")] public string? BosToken { get; set; }
    [JsonPropertyName("eos_token")] public string? EosToken { get; set; }
    [JsonPropertyName("chat_template")] public string? ChatTemplate { get; set; }
    [JsonPropertyName("model_path")] public string? ModelPath { get; set; }
}
