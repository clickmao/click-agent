namespace agent.modelqueue;

/// <summary>
/// R380 (用户钦定, **首要 KPI**): prompt 缓存**红线闸门 + 越线必查**。
///
/// 红线: 多轮会话 **第 2 轮起** 有效命中率 ≥ **95%** (用户 OOB 提高; 目标 98~99%)。
/// 算术前提 (R380 实测): 命中上限 ≈ 1 − 1/n (n = 前缀 64-token 单元数) ⇒ 前缀须 ≥
/// <see cref="PromptCacheKpi.PrefixTokensNeededFor"/> 给出的量级 (95% ⇒ ≥1280 token), 否则**必然越线**。
/// 口径: 见 <see cref="PromptCacheKpi"/> —— 只算「需要命中的部分」, 本轮新增不计入分母。
///
/// 用户逐字: **"一旦越过红线必然检查问题为什么发生并修复"** ⇒ 越线不得只记一个数字了事:
///   必须**同时**产出按实测根因排序的可执行诊断 (R379 实证四类破坏点), 否则下一轮仍不知断在哪。
/// </summary>
public static class PromptCacheRedline
{
    /// <summary>红线阈值 (用户钦定, R380 OOB 由 90% 提高到 **95%**): 多轮第 2 轮起有效命中率 ≥ 95%。</summary>
    public const double Threshold = 0.95;

    /// <summary>生效最小轮次: 第 1 轮是冷启动 (无"需要命中"的部分), 不参与判定。</summary>
    public const int MinTurn = 2;

    /// <summary>该轮是否参与红线判定 (轮次达标 且 存在"需要命中"的部分)。</summary>
    public static bool Applies(int turn, int cacheableTokens) => turn >= MinTurn && cacheableTokens > 0;

    /// <summary>是否越线 (有效命中率有值且低于阈值)。</summary>
    public static bool Violated(int turn, int cacheableTokens, double effectiveRate)
        => Applies(turn, cacheableTokens) && effectiveRate >= 0 && effectiveRate < Threshold;

    /// <summary>
    /// 越线必查: 输出多行可执行诊断 (数值 + 按 R379 实测根因排序的排查清单)。
    /// 直接落日志与遥测 (cache_redline_violation.diagnosis), 便于离线报告逐条答复"为什么"。
    /// </summary>
    public static string Diagnose(int turn, int promptTokens, int cacheableTokens, int hit, int miss, int lastPromptTokens)
    {
        var growth = promptTokens - cacheableTokens;
        var h = hit < 0 ? 0 : hit;
        var gap = cacheableTokens - h;
        var rate = cacheableTokens > 0 ? Math.Round(h / (double)cacheableTokens, 4) : -1d;
        var ceiling = PromptCacheKpi.HitCeiling(cacheableTokens);
        var need = PromptCacheKpi.PrefixTokensNeededFor(Threshold);
        var ceilingNote = cacheableTokens > 0 && ceiling <= cacheableTokens * Threshold
            ? $"  ★算术判决: 前缀仅 {cacheableTokens} token → 上限 {ceiling} 命中 ({(ceiling / (double)cacheableTokens):P2}), 结构修复到此为止; "
              + $"达 {Threshold:P0} 需前缀 ≥ {need} token (加厚会话稳定前缀/首轮召回), 否则必然越线"
            : $"  (前缀 {cacheableTokens} token 的上限 {ceiling} 命中足够达线 → 属结构性问题, 按下列清单查)";
        return string.Join("\n", new[]
        {
            $"越线: 轮 {turn} 有效命中率 {rate} < {Threshold}",
            $"数值: prompt={promptTokens} 需要命中={cacheableTokens}(上轮 {lastPromptTokens}) 命中={hit} 未命中={miss} 本轮新增={growth} 缺口={gap}",
            "按实测根因逐项查 (R379 四类破坏点):",
            "  ① messages[0] 是否被逐轮改写? system 必须会话内恒定字节 (意图/预测/时间戳一律走尾部追加区)",
            "  ② 历史是否被重写/摘要/砍头? 必须追加式回放; 预算 1M 不应触发丢弃; 发送字节=回放字节 (SentContent)",
            "  ③ 上一轮发送字节与本轮回放字节是否逐字节一致? 回注/修复/续写块必须在 SentContent 快照之前落定",
            "  ④ 本轮增量是否过大? 静态块应首轮焊进前缀; 动态块应跨轮去重; 观察 新增/前缀 占比",
            "  ⑤ 缺口 ≤64 token 时属于缓存单元 (64 token) 边界对齐损耗, 正常, 不必修",
            ceilingNote,
        });
    }
}
