using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;


/// <summary>
/// 本地生成结果。记账口径 (R411 钉死, 勿改): <see cref="TokensEvaluated"/> = 本轮 prompt 总长,
/// <see cref="PromptNewTokens"/> = 新评估数, <see cref="CachedTokens"/> = 命中复用数;
/// 恒等: TokensEvaluated == PromptNewTokens + CachedTokens。
/// </summary>
public sealed class LocalGenerationOutcome
{
    public bool Success { get; init; }
    public string Content { get; init; } = string.Empty;
    public int TokensEvaluated { get; init; }
    public int PromptNewTokens { get; init; }
    public int CachedTokens { get; init; }
    public int GeneratedTokens { get; init; }
    public long ElapsedMs { get; init; }
    public string? Error { get; init; }
    public string Model { get; init; } = "local";

    /// <summary>R430: prompt 指纹 (SHA-256 前 16 hex; 空 = 后端未上报 — 缺失不等于错误)。</summary>
    public string PromptSha16 { get; init; } = string.Empty;

    /// <summary>R430: 请求体指纹 (覆盖全部请求字段: n_predict/samplers/cache_prompt/seed...)。</summary>
    public string RequestSha16 { get; init; } = string.Empty;

    /// <summary>R430: 请求关键字段摘要 (指纹不同时用于定位)。</summary>
    public string RequestFields { get; init; } = string.Empty;

    /// <summary>记账恒等校验 (口径一致才可采信; 违规 ⇒ 该次结果作废并降级远端)。</summary>
    public bool AccountingConsistent => TokensEvaluated == PromptNewTokens + CachedTokens;
}
