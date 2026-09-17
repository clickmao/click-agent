using System.Text.Json.Serialization;

namespace agent.llamacpp;

// ── llama-server 线协议 DTO (AOT: 全部走 JsonSerializerContext 源生成, 禁反射) ──

internal sealed class CompletionRequest
{
    [JsonPropertyName("prompt")] public string Prompt { get; set; } = string.Empty;
    [JsonPropertyName("n_predict")] public int NPredict { get; set; } = 64;
    [JsonPropertyName("samplers")] public string[] Samplers { get; set; } = ["temperature"];
    [JsonPropertyName("temperature")] public float Temperature { get; set; }
    [JsonPropertyName("top_k")] public int TopK { get; set; }
    [JsonPropertyName("top_p")] public float TopP { get; set; } = 1f;
    [JsonPropertyName("min_p")] public float MinP { get; set; }
    [JsonPropertyName("repeat_penalty")] public float RepeatPenalty { get; set; } = 1f;
    [JsonPropertyName("seed")] public int Seed { get; set; }
    [JsonPropertyName("cache_prompt")] public bool CachePrompt { get; set; }
    [JsonPropertyName("return_tokens")] public bool ReturnTokens { get; set; } = true;
    [JsonPropertyName("stream")] public bool Stream { get; set; }
    [JsonPropertyName("n_probs")] public int NProbs { get; set; }
}
