using System.Text.Json.Serialization;

namespace agent.modelqueue;


public sealed class OpenAIChatUsage
{
    [JsonPropertyName("prompt_tokens")]
    public int PromptTokens { get; set; }

    [JsonPropertyName("completion_tokens")]
    public int CompletionTokens { get; set; }

    [JsonPropertyName("total_tokens")]
    public int TotalTokens { get; set; }

    /// <summary>
    /// R377 (用户钦定 KPI): DeepSeek 上下文缓存命中 token 数 (usage.prompt_cache_hit_tokens)。
    /// **可空 = provider 未上报** —— 与"命中 0"是两回事, 不得用 0 冒充 (KPI 侧记 -1)。
    /// 命中率 = hit / (hit + miss), 反映可复用前缀 (系统提示/工具定义/长文档) 的复用程度。
    /// </summary>
    [JsonPropertyName("prompt_cache_hit_tokens")]
    public int? PromptCacheHitTokens { get; set; }

    /// <summary>R377: 未命中缓存的 prompt token 数 (usage.prompt_cache_miss_tokens)。可空 = 未上报。</summary>
    [JsonPropertyName("prompt_cache_miss_tokens")]
    public int? PromptCacheMissTokens { get; set; }
}
