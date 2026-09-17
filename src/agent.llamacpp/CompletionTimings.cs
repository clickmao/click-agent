using System.Text.Json.Serialization;

namespace agent.llamacpp;


internal sealed class CompletionTimings
{
    [JsonPropertyName("prompt_ms")] public double PromptMs { get; set; }
    [JsonPropertyName("predicted_ms")] public double PredictedMs { get; set; }
    [JsonPropertyName("prompt_per_second")] public double PromptPerSecond { get; set; }
    [JsonPropertyName("predicted_per_second")] public double PredictedPerSecond { get; set; }

    /// <summary>服务端自报的「从缓存复用的前缀 token 数」(K2b 记账锚点; 不是估算值)。</summary>
    [JsonPropertyName("cache_n")] public int CacheN { get; set; }
}
