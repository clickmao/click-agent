using System.Net.Http.Json;
using System.Text.Json;
using agent.modelqueue;   // R430: LocalInputFingerprint (共享层; 不引入反向依赖)

namespace agent.llamacpp;


/// <summary>单次生成请求参数。默认口径 = R407 对账口径: 仅 temperature 采样器 + temp 0 (greedy)、关 cache_prompt。</summary>
public sealed record CompletionOptions
{
    public required string Prompt { get; init; }
    public int MaxTokens { get; init; } = 64;
    public string[] Samplers { get; init; } = ["temperature"];
    public float Temperature { get; init; }
    public int TopK { get; init; }
    public float TopP { get; init; } = 1f;
    public float MinP { get; init; }
    public float RepeatPenalty { get; init; } = 1f;
    public int Seed { get; init; }

    /// <summary>
    /// 是否启用服务端前缀缓存 (llama-server cache_prompt)。
    /// 对账口径必须关: 文档明示启用后不同 batch 的 logits 不保证逐位一致 ⇒ 对账不可复现；
    /// 生产口径必须开: 可复用长前缀是 K2b 的唯一来源。两者混用会把精度差误判成引擎缺陷。
    /// </summary>
    public bool CachePrompt { get; init; }

    public bool ReturnTokens { get; init; } = true;
}
