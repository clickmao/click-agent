using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using agent.llamacpp;
using agent.modelqueue;

namespace agent.host;


/// <summary>
/// R411 单轮读数。口径（独立实现钉死，**别按字段名猜**）:
/// <see cref="PromptTokens"/> = **总长** = llama.cpp <c>tokens_evaluated</c>（含 BOS）；
/// <see cref="PromptTokensRecomputed"/> = 总长 − 命中 = <c>timings.prompt_n</c>。
/// </summary>
public sealed class LlamaCppSessionTurnResult
{
    public int Turn { get; set; }
    /// <summary>本轮 prompt 总长（tokens_evaluated）。</summary>
    public int PromptTokens { get; set; }
    /// <summary>本轮重算 token 数（总长 − 命中）。</summary>
    public int PromptTokensRecomputed { get; set; }
    public int CachedTokens { get; set; }
    /// <summary>本轮生成 token 数（下一轮的可复用上限 = 本轮总长 + 本轮生成）。</summary>
    public int GeneratedTokens { get; set; }
    /// <summary>可复用上限 = 上一轮总长 + 上一轮生成（首轮 0）。</summary>
    public int CarryOverTokens { get; set; }
    /// <summary>携带复用率 = 命中 / 可复用上限（R380 口径的本地等价物）。</summary>
    public double CarryOverReuse { get; set; } = -1;
    /// <summary>会话整体复用率 = 命中 / 本轮总长（直接决定 token 成本）。</summary>
    public double SessionReuseRatio { get; set; } = -1;
    /// <summary>本会话冷启首轮总长（≈ 常驻前缀厚度）。</summary>
    public int PrefixTokens { get; set; }
    /// <summary>前缀绝对长度是否达稳健界（4224 token）。</summary>
    public bool PrefixLengthSatisfied { get; set; }
    public bool RedlineApplies { get; set; }
    public bool Violated { get; set; }
    public string? Diagnosis { get; set; }
    public string? Content { get; set; }
    /// <summary>每轮都必须 = 1 ⇒ 长驻（>1 = 发生重启，前序 KV 缓存已丢）。</summary>
    public long ProcessStarts { get; set; }
}
