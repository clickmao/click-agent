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

internal sealed class CompletionTimings
{
    [JsonPropertyName("prompt_ms")] public double PromptMs { get; set; }
    [JsonPropertyName("predicted_ms")] public double PredictedMs { get; set; }
    [JsonPropertyName("prompt_per_second")] public double PromptPerSecond { get; set; }
    [JsonPropertyName("predicted_per_second")] public double PredictedPerSecond { get; set; }
}

internal sealed class CompletionResponse
{
    [JsonPropertyName("content")] public string? Content { get; set; }
    [JsonPropertyName("tokens")] public int[]? Tokens { get; set; }
    [JsonPropertyName("tokens_predicted")] public int TokensPredicted { get; set; }
    [JsonPropertyName("tokens_evaluated")] public int TokensEvaluated { get; set; }
    [JsonPropertyName("stop")] public bool Stop { get; set; }
    [JsonPropertyName("timings")] public CompletionTimings? Timings { get; set; }
}

internal sealed class EmbeddingRequest
{
    [JsonPropertyName("input")] public string[] Input { get; set; } = [];
    [JsonPropertyName("model")] public string Model { get; set; } = "local";
    [JsonPropertyName("encoding_format")] public string EncodingFormat { get; set; } = "float";
}

internal sealed class EmbeddingData
{
    [JsonPropertyName("index")] public int Index { get; set; }
    [JsonPropertyName("embedding")] public float[] Embedding { get; set; } = [];
}

internal sealed class EmbeddingResponse
{
    [JsonPropertyName("data")] public EmbeddingData[] Data { get; set; } = [];
}

internal sealed class HealthResponse
{
    [JsonPropertyName("status")] public string? Status { get; set; }
}

[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
[JsonSerializable(typeof(CompletionRequest))]
[JsonSerializable(typeof(CompletionResponse))]
[JsonSerializable(typeof(EmbeddingRequest))]
[JsonSerializable(typeof(EmbeddingResponse))]
[JsonSerializable(typeof(HealthResponse))]
internal sealed partial class LlamaCppJsonContext : JsonSerializerContext;
