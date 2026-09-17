using Microsoft.Extensions.Logging;

namespace agent.modelqueue;


/// <summary>
/// 一次本地生成的 K2b 观测（纯数据，可直接断言；不含 I/O）。
/// </summary>
/// <param name="SessionKey">会话键（空串 = 无会话归属，逐轮记账不参与）。</param>
/// <param name="TurnIndex">轮次（第 1 轮 = 冷启动，红线不适用）。</param>
/// <param name="PromptTokens">本轮 prompt **总长**（llama.cpp <c>tokens_evaluated</c>；独立实现已钉死语义）。</param>
/// <param name="CachedTokens">本轮复用 token 数（llama.cpp <c>cache_n</c>）；**-1 = 未上报**。</param>
/// <param name="RecomputedTokens">本轮实际重算 token 数（总长 − 命中）。</param>
/// <param name="CarryOverTokens">可复用上限（上一轮 prompt + 上一轮生成）；0 = 不适用。</param>
/// <param name="CarryOverReuse">携带复用率 = 命中 / 可复用上限；-1 = 未上报/无分母/口径不符（弃权）。</param>
/// <param name="SessionReuseRatio">会话整体复用率 = 命中 / 本轮总长（**直接决定 token 成本**，与远端口径互为补充）。</param>
/// <param name="PrefixTokens">本会话冷启首轮总长（≈ 常驻前缀厚度）。</param>
/// <param name="PrefixLengthSatisfied">前缀绝对长度是否达红线所需的稳健界（R410: 比值不是 KPI，绝对长度才是）。</param>
/// <param name="RedlineApplies">该轮是否参与红线判定（轮次 ≥2 且存在可复用部分）。</param>
/// <param name="Violated">是否越线（比值或绝对长度任一不达标）。</param>
/// <param name="Diagnosis">越线时的可执行诊断，否则 null。</param>
public readonly record struct LocalCacheObservation(
    string SessionKey,
    int TurnIndex,
    int PromptTokens,
    int CachedTokens,
    int RecomputedTokens,
    int CarryOverTokens,
    double CarryOverReuse,
    double SessionReuseRatio,
    int PrefixTokens,
    bool PrefixLengthSatisfied,
    bool RedlineApplies,
    bool Violated,
    string? Diagnosis);
