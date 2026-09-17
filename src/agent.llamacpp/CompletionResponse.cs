using System.Text.Json.Serialization;

namespace agent.llamacpp;


internal sealed class CompletionResponse
{
    [JsonPropertyName("content")] public string? Content { get; set; }
    [JsonPropertyName("tokens")] public int[]? Tokens { get; set; }
    [JsonPropertyName("tokens_predicted")] public int TokensPredicted { get; set; }
    [JsonPropertyName("tokens_evaluated")] public int TokensEvaluated { get; set; }
    [JsonPropertyName("stop")] public bool Stop { get; set; }
    [JsonPropertyName("timings")] public CompletionTimings? Timings { get; set; }
}
