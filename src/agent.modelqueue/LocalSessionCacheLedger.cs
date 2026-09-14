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

/// <summary>
/// R411: **本地生成侧的 K2b 台账** —— 把 llama.cpp 本地生成接进产品既有 K2b 口径，
/// 但**分母按本地引擎自己的语义算**，不套远端 provider 的经验界。
///
/// 为什么必须分开（本轮实测教训）:
///   远端 provider 的「需要命中的部分」= min(本轮, 上一轮 prompt)，并按 64-token 单元打折
///   （mt_fix4 实测规律）；而 llama.cpp 的 KV 缓存**连上一轮生成的 token 一起持有**
///   ⇒ 直接套远端分母会把物理上正常的复用（命中 &gt; 上一轮 prompt）判成「口径错误」。
///
/// 语义映射（唯一映射点，改这里即改全部本地判定）:
///   • 命中 = <c>cache_n</c>（服务端真实复用 token，非估算）；总长 = <c>tokens_evaluated</c>；
///   • 重算 = 总长 − 命中（= <c>timings.prompt_n</c>）；
///   • 可复用上限 = 上一轮 prompt + 上一轮生成（缺省退化为上一轮 prompt）；
///   • **判据 = 合取**: 携带复用率 ≥ 97% **且** 前缀绝对长度 ≥ 4224（R410: 比值不是 KPI）；
///   • 命中 &gt; 可复用上限 ⇒ **弃权**（口径不符，记 -1，绝不硬套一个判决）。
///
/// 端口化纪律: 入参全基元、零 llama.cpp 类型依赖 ⇒ 可单测、可换生成器；
/// 被使用计数 Observations / Violations / NotApplicable；越线同时落 LogWarning + 遥测。
/// </summary>
public sealed class LocalSessionCacheLedger
{
    /// <summary>遥测 source（与远端 ModelQueueRouter 区分；字段名相同 ⇒ 同一聚合可见）。</summary>
    public const string DefaultSource = "LlamaCppTextGenerator";

    private const int MaxSessions = 512;

    private readonly System.Collections.Concurrent.ConcurrentDictionary<string, int> _lastPromptTokens = new(StringComparer.Ordinal);
    private readonly System.Collections.Concurrent.ConcurrentDictionary<string, int> _prefixTokens = new(StringComparer.Ordinal);
    private readonly ILogger? _logger;
    private long _observations;
    private long _violations;
    private long _notApplicable;
    private long _abstained;

    public LocalSessionCacheLedger(ILogger? logger = null) => _logger = logger;

    /// <summary>被使用计数: 观测次数。</summary>
    public long Observations => Interlocked.Read(ref _observations);

    /// <summary>被使用计数: 越线次数（红线变红次数；0 不一定是好事 —— 见负控测试）。</summary>
    public long Violations => Interlocked.Read(ref _violations);

    /// <summary>被使用计数: 不适用次数（首轮/未上报/无分母 —— 与「达标」严格区分）。</summary>
    public long NotApplicable => Interlocked.Read(ref _notApplicable);

    /// <summary>被使用计数: 弃权次数（命中 &gt; 可复用上限 ⇒ 口径不符，不出判决）。</summary>
    public long Abstained => Interlocked.Read(ref _abstained);

    /// <summary>红线所需的**前缀绝对长度**稳健界（R410 口径: 97% ⇒ 4224 token）。</summary>
    public static int RequiredPrefixTokens => PromptCacheKpi.PrefixTokensNeededFor(PromptCacheRedline.Threshold);

    /// <summary>
    /// 纯函数式记账 + 打点。<paramref name="cachedTokens"/> 传 -1 表示 provider 未上报；
    /// <paramref name="carryOverCeiling"/> 传 0 表示未知（退化为「上一轮 prompt」）。
    /// </summary>
    public LocalCacheObservation Observe(
        string? sessionKey,
        int turnIndex,
        int promptTokens,
        int cachedTokens,
        int carryOverCeiling = 0,
        string? model = null,
        string source = DefaultSource)
    {
        var key = sessionKey ?? string.Empty;
        var last = key.Length > 0 && _lastPromptTokens.TryGetValue(key, out var prev) ? prev : 0;

        // 铁律①: 未上报 ≠ 0 命中。
        int? hit = cachedTokens < 0 ? null : cachedTokens;
        var recomputed = hit is null ? promptTokens : Math.Max(0, promptTokens - hit.Value);

        var ceilingRaw = carryOverCeiling > 0 ? carryOverCeiling : last;
        var carryOver = Math.Min(promptTokens, ceilingRaw);
        var prefixTokens = key.Length > 0 && _prefixTokens.TryGetValue(key, out var pt) ? pt : promptTokens;
        if (turnIndex <= 1 && key.Length > 0) { if (_prefixTokens.Count > MaxSessions) _prefixTokens.Clear(); _prefixTokens[key] = promptTokens; prefixTokens = promptTokens; }

        // 弃权: 命中超出可复用上限 ⇒ 本轮的「可复用上限」模型与实际不符（口径错），不出判决。
        var abstain = hit is not null && hit.Value > carryOver;
        var carryOverReuse = hit is null || abstain || carryOver <= 0 ? PromptCacheKpi.Unknown : Math.Round(hit.Value / (double)carryOver, 4);
        var ratio = hit is null || promptTokens <= 0 ? PromptCacheKpi.Unknown : Math.Round(hit.Value / (double)promptTokens, 4);
        var prefixOk = prefixTokens >= RequiredPrefixTokens;
        // 铁律②: 未上报(命中为 null) 既不算达标也不算越线 ——「没测到」不得判红（缺失≠错误）。
        var applies = PromptCacheRedline.Applies(turnIndex, carryOver) && !abstain && hit is not null;
        var violated = applies && (carryOverReuse < PromptCacheRedline.Threshold || !prefixOk);

        var fields = PromptCacheKpi.Fields(hit, hit is null ? null : recomputed);
        agent.config.AgentTelemetry.Emit("llm_call", source,
            ("model", model ?? "local-llamacpp"), ("provider", "llamacpp"),
            ("agent_session", key), ("turn", turnIndex),
            ("prompt_tokens", promptTokens), ("prompt_total_tokens", promptTokens),
            ("cached_tokens", hit ?? PromptCacheKpi.Unknown),
            ("recomputed_tokens", recomputed),
            ("carry_over_tokens", carryOver),
            ("carry_over_reuse", carryOverReuse),
            ("session_reuse_ratio", ratio),
            ("prefix_tokens", prefixTokens),
            fields[0], fields[1], fields[2]);

        string? diagnosis = null;
        if (violated)
        {
            diagnosis = Diagnose(turnIndex, promptTokens, recomputed, carryOver, carryOverReuse, ratio, prefixTokens, prefixOk);
            _logger?.LogWarning("LlamaCpp(本地): prompt 缓存红线越线 — {Diag}", diagnosis);
            agent.config.AgentTelemetry.Emit("cache_redline_violation", source,
                ("agent_session", key), ("turn", turnIndex),
                ("carry_over_reuse", carryOverReuse), ("session_reuse_ratio", ratio),
                ("carry_over_tokens", carryOver), ("prefix_tokens", prefixTokens),
                ("prefix_length_satisfied", prefixOk),
                ("hit", PromptCacheKpi.HitTokens(hit)), ("miss", PromptCacheKpi.MissTokens(hit is null ? null : recomputed)),
                ("prompt_tokens", promptTokens), ("last_prompt_tokens", last),
                ("threshold", PromptCacheRedline.Threshold), ("diagnosis", diagnosis));
            Interlocked.Increment(ref _violations);
        }
        if (abstain) Interlocked.Increment(ref _abstained);
        if (!applies && !violated) Interlocked.Increment(ref _notApplicable);

        // 记账必须在判定之后: 存「本轮已发 prompt」，供下一轮算可复用上限。
        if (key.Length > 0)
        {
            if (_lastPromptTokens.Count > MaxSessions) _lastPromptTokens.Clear();
            _lastPromptTokens[key] = promptTokens;
        }
        Interlocked.Increment(ref _observations);

        return new LocalCacheObservation(key, turnIndex, promptTokens,
            hit ?? PromptCacheKpi.Unknown, recomputed, carryOver, carryOverReuse, ratio,
            prefixTokens, prefixOk, applies, violated, diagnosis);
    }

    /// <summary>越线诊断（本地口径: 比值 + **绝对长度** 双条件，附本地引擎特有的排查项）。</summary>
    private static string Diagnose(int turnIndex, int promptTokens, int recomputed, int carryOver,
        double carryOverReuse, double ratio, int prefixTokens, bool prefixOk)
    {
        var need = RequiredPrefixTokens;
        var head = $"LlamaCpp(本地) K2b 越线(turn={turnIndex}, 阈值={PromptCacheRedline.Threshold:P0}): "
                 + $"前缀绝对长度 {prefixTokens} token (需 ≥{need}, 满足={prefixOk}) | "
                 + $"携带复用率={carryOverReuse:P2} (命中/可复用上限 {carryOver}) | "
                 + $"会话整体复用率={ratio:P2} (总长 {promptTokens}, 重算 {recomputed})";
        var cause = !prefixOk
            ? "★算术判决: 常驻前缀本身不足 ⇒ 无论引擎多好都不可能稳定达线（R410: 比值不是 KPI，绝对长度才是）; 处置=加厚常驻 system 前缀/首轮召回"
            : "前缀厚度已够 ⇒ 属结构性问题，按下列清单查";
        return string.Join("\n", new[]
        {
            head,
            "  " + cause,
            "  ① 助手轮回放是否与生成**逐字节一致**（含 think/思考块与模板骨架；不一致 ⇒ 命中在助手轮断裂，只剩 system 前缀可复用）",
            "  ② 每轮增量（助手回复 + 用户输入）是否过大 ⇒ 增量/总长 直接压低比值（短回复/长前缀才可能稳过）",
            "  ③ 是否同进程同 server（跨进程 ⇒ KV 缓存不存在，命中必为 0）",
        });
    }

    /// <summary>该会话上一轮已发 prompt token 数（诊断/断言用；无 → 0）。</summary>
    public int LastPromptTokensFor(string? sessionKey)
        => string.IsNullOrEmpty(sessionKey) ? 0 : (_lastPromptTokens.TryGetValue(sessionKey, out var v) ? v : 0);

    /// <summary>该会话冷启首轮总长 ≈ 常驻前缀厚度（诊断/断言用；无 → 0）。</summary>
    public int PrefixTokensFor(string? sessionKey)
        => string.IsNullOrEmpty(sessionKey) ? 0 : (_prefixTokens.TryGetValue(sessionKey, out var v) ? v : 0);
}
