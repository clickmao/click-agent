namespace agent.modelqueue;

/// <summary>
/// R380 (用户钦定, **首要 KPI**): prompt 缓存**红线闸门 + 越线必查**。
///
/// 红线: 多轮会话 **第 2 轮起** 有效命中率 ≥ **97%** (R393 用户 OOB: 由 95% 提高到 97%; 目标 98~99%)。
/// 算术前提 (R380 实测): 命中上限 = (⌊P/64⌋ − 1) × 64 ⇒ 前缀须 ≥
/// <see cref="PromptCacheKpi.PrefixTokensNeededFor"/> 的**最坏对齐稳健界**, 否则**必然越线**:
///   **97% ⇒ ≥4224 token (66 单元)**; 95% ⇒ ≥2496; 98% ⇒ ≥6336。
/// (对齐最优时 97% 也需 ≥2176 token —— 越线诊断/加厚方案按稳健界取, 不按最优界。)
/// 口径: 见 <see cref="PromptCacheKpi"/> —— 只算「需要命中的部分」, 本轮新增不计入分母。
///
/// 用户逐字: **"一旦越过红线必然检查问题为什么发生并修复"** ⇒ 越线不得只记一个数字了事:
///   必须**同时**产出按实测根因排序的可执行诊断 (R379 实证四类破坏点), 否则下一轮仍不知断在哪。
/// </summary>
public static class PromptCacheRedline
{
    /// <summary>
    /// 红线阈值 (用户钦定): R380 OOB 由 90% 提高到 95%; **R393 OOB 再由 95% 提高到 97%**
    /// (目标 98~99% 不变)。改此常量即改判定与诊断文案; `scripts/kpi_cache_hit.py` 的 REDLINE
    /// 由机检锁死同值 (阈值散落两处必漂移)。
    /// </summary>
    public const double Threshold = 0.97;

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
        => Diagnose(turn, promptTokens, cacheableTokens, hit, miss, lastPromptTokens, PromptCacheKpi.Unknown);

    /// <summary>R476: 带用户轮长度的诊断 (追加分档行; 旧重载语义一字不动)。</summary>
    public static string Diagnose(int turn, int promptTokens, int cacheableTokens, int hit, int miss, int lastPromptTokens, int userTurnTokens)
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
            BandLine(promptTokens, cacheableTokens, userTurnTokens),
            ceilingNote,
        });
    }

    // ─────────────────────────── R476: 红线判定**分档化** (只增不改) ───────────────────────────
    //
    // R469 结论 (逐字口径): 命中率 = 1 − 新/前缀, 其中**用户轮长度不可压** ⇒ 单值 97% 对长轮
    // **结构性不可达**。故判定器须给出**分档目标**: 短档目标 = 红线 0.97 (用户钦定, 不变);
    // 长档目标 = min(0.97, 结构上限)。上限模型与 R469 器具逐字同形 (见 eval/rover/r469/hit_ceiling_bands.py:45):
    //     new      = 用户轮 + 21 (承接增量, 实测 15~21 字 ⇒ 取上界)
    //     ceiling  = prefix / (prefix + new)
    // 判据 (达成轮占比): at_target / (below_ceiling + below_target) 按档、按通道分别报。

    /// <summary>R469 实测承接增量上界 (本地/远端承接 15~21 字符 ⇒ 取 21)。</summary>
    public const int TurnOverheadTokens = 21;

    /// <summary>用户轮长度分档 (token); 依据 R469 真实 400 轮抽样。</summary>
    public static readonly (int Lo, int Hi)[] TurnBands =
    {
        (0, 30), (31, 93), (94, 200), (201, int.MaxValue),
    };

    /// <summary>档序号 (0..3); 用户轮长度未知/负 ⇒ -1 (不参与分档判定, 禁按 0 冒充)。</summary>
    public static int BandOf(int userTurnTokens)
    {
        if (userTurnTokens < 0) return -1;
        for (var i = 0; i < TurnBands.Length; i++)
        {
            if (userTurnTokens >= TurnBands[i].Lo && userTurnTokens <= TurnBands[i].Hi) return i;
        }
        return TurnBands.Length - 1;
    }

    /// <summary>档标签 (与 r469 夹具 key 同形): "0-30" / "31-93" / "94-200" / "201+"。</summary>
    public static string BandLabel(int band)
        => band < 0 || band >= TurnBands.Length
            ? "unknown"
            : (TurnBands[band].Hi == int.MaxValue
                ? $"{TurnBands[band].Lo}+"
                : $"{TurnBands[band].Lo}-{TurnBands[band].Hi}");

    /// <summary>结构上限 (理论上限, 假定前缀逐字节稳定 ⇒ 可缓存): prefix / (prefix + 用户轮 + 21)。</summary>
    public static double CeilingFor(int prefixTokens, int userTurnTokens)
    {
        if (prefixTokens <= 0 || userTurnTokens < 0) return PromptCacheKpi.Unknown;
        return prefixTokens / (double)(prefixTokens + userTurnTokens + TurnOverheadTokens);
    }

    /// <summary>该轮目标命中率 = min(红线, 结构上限); 用户轮未知 ⇒ 红线 (档未知不降目标)。</summary>
    public static double TargetFor(int prefixTokens, int userTurnTokens)
    {
        if (userTurnTokens < 0) return Threshold;
        var c = CeilingFor(prefixTokens, userTurnTokens);
        return c < 0 ? Threshold : Math.Min(Threshold, c);
    }

    /// <summary>容差 = 一个缓存单元的占比 (R469 报告 ⑤: 64 token 对齐损耗属正常)。</summary>
    public static double ToleranceFor(int prefixTokens)
        => prefixTokens > 0 ? PromptCacheKpi.CacheUnitTokens / (double)prefixTokens : 0d;

    /// <summary>使目标成立所需最小前缀: (用户轮 + 21) × target / (1 − target)。</summary>
    public static double PrefixTokensNeededForBand(int userTurnTokens, double target)
    {
        if (userTurnTokens < 0 || target <= 0 || target >= 1) return PromptCacheKpi.Unknown;
        return (userTurnTokens + TurnOverheadTokens) * target / (1 - target);
    }

    /// <summary>分档判定结果 (与 scripts/kpi_cache_hit.py 的 verdict 串逐字同值)。</summary>
    public static class BandVerdict
    {
        public const string NotApplicable = "not_applicable";   // 首轮冷启动 / 无"需要命中"部分
        public const string Unreported = "unreported";          // 命中率未上报 (-1)
        public const string AtTarget = "at_target";             // ≥ 目标 − 容差
        public const string BelowCeiling = "below_ceiling";     // 未达上限 ⇒ 结构性可修
        public const string BelowTarget = "below_target";       // 短档未达红线
    }

    /// <summary>
    /// 分档判定 (纯函数)。rate 为 effective_hit_rate (= 1 − 新/前缀)。
    /// - 轮次/需要命中面不适用 ⇒ not_applicable; 未上报(-1) ⇒ unreported (禁按 0 计入达成率)。
    /// - rate ≥ target − tol ⇒ at_target;
    /// - 否则若 target ≥ 红线 (短档, 目标未被上限压低) ⇒ below_target;
    /// - 否则 ⇒ below_ceiling (上限本身高于实际 ⇒ 有结构空间可修)。
    /// </summary>
    public static string JudgeBand(int turn, int cacheableTokens, int prefixTokens, int userTurnTokens, double rate)
    {
        if (!Applies(turn, cacheableTokens)) return BandVerdict.NotApplicable;
        if (rate < 0) return BandVerdict.Unreported;
        var target = TargetFor(prefixTokens, userTurnTokens);
        if (target < 0) return BandVerdict.Unreported;
        var tol = ToleranceFor(prefixTokens);
        if (rate + tol >= target) return BandVerdict.AtTarget;
        return target >= Threshold ? BandVerdict.BelowTarget : BandVerdict.BelowCeiling;
    }

    /// <summary>余量 (target − rate); 任一未知 ⇒ -1。</summary>
    public static double MarginFor(int prefixTokens, int userTurnTokens, double rate)
        => rate < 0 ? PromptCacheKpi.Unknown : TargetFor(prefixTokens, userTurnTokens) - rate;

    // ── 实测通道 (growth = prompt − 需要命中, 调用点可直接量到, 不需猜用户轮) ──
    // 注意: growth **含**用户轮 + 承接 + 本轮注入 ⇒ growth ≥ 用户轮 ⇒ 由 growth 派生的档是
    // 用户轮档的**上偏**代理, 故 telemetry 必须带 band_source 声明口径 (禁把代理当实测档)。

    /// <summary>实测通道口径标记: 档由用户轮长度得出 (真值)。</summary>
    public const string BandSourceUserTurn = "user_turn";
    /// <summary>实测通道口径标记: 档由 growth 上偏代理得出 (调用点无用户轮长度)。</summary>
    public const string BandSourceGrowthProxy = "growth_upper_bound";
    /// <summary>口径标记: 档未知。</summary>
    public const string BandSourceUnknown = "unknown";

    /// <summary>实测上限: 需要命中 / (需要命中 + 本轮新增)。</summary>
    public static double CeilingFromGrowth(int cacheableTokens, int growthTokens)
    {
        if (cacheableTokens <= 0 || growthTokens < 0) return PromptCacheKpi.Unknown;
        return cacheableTokens / (double)(cacheableTokens + growthTokens);
    }

    /// <summary>实测目标 = min(红线, 实测上限)。</summary>
    public static double TargetFromGrowth(int cacheableTokens, int growthTokens)
    {
        var c = CeilingFromGrowth(cacheableTokens, growthTokens);
        return c < 0 ? Threshold : Math.Min(Threshold, c);
    }

    /// <summary>实测通道分档判定 (调用点用): growth = prompt − cacheable。</summary>
    public static string JudgeByGrowth(int turn, int cacheableTokens, int promptTokens, double rate)
    {
        if (!Applies(turn, cacheableTokens)) return BandVerdict.NotApplicable;
        if (rate < 0) return BandVerdict.Unreported;
        var growth = promptTokens - cacheableTokens;
        if (growth < 0) return BandVerdict.Unreported;
        var target = TargetFromGrowth(cacheableTokens, growth);
        if (rate + ToleranceFor(cacheableTokens) >= target) return BandVerdict.AtTarget;
        return target >= Threshold ? BandVerdict.BelowTarget : BandVerdict.BelowCeiling;
    }

    /// <summary>
    /// llm_call 面上的分档字段 (纯函数, AOT 安全)。band = 由 growth 上偏代理得的档;
    /// 用户轮长度未知 ⇒ 且 growth 也未知时 band_source=unknown。
    /// </summary>
    public static (string Key, object? Value)[] BandFields(int turn, int cacheableTokens, int promptTokens, double rate)
    {
        var growth = cacheableTokens > 0 ? promptTokens - cacheableTokens : PromptCacheKpi.Unknown;
        var band = growth < 0 ? -1 : BandOf(growth);
        var source = !Applies(turn, cacheableTokens)
            ? BandSourceUnknown
            : (growth < 0 ? BandSourceUnknown : BandSourceGrowthProxy);
        var ceil = growth < 0 ? PromptCacheKpi.Unknown : CeilingFromGrowth(cacheableTokens, growth);
        var target = growth < 0 ? PromptCacheKpi.Unknown : TargetFromGrowth(cacheableTokens, growth);
        var margin = (rate < 0 || target < 0) ? PromptCacheKpi.Unknown : Math.Round(target - rate, 4);
        return new (string, object?)[]
        {
            ("cache_band", band),
            ("cache_band_source", source),
            ("cache_band_growth", growth),
            ("cache_ceiling", ceil < 0 ? PromptCacheKpi.Unknown : Math.Round(ceil, 4)),
            ("cache_target", target < 0 ? PromptCacheKpi.Unknown : Math.Round(target, 4)),
            ("cache_margin", margin),
            ("cache_band_verdict", JudgeByGrowth(turn, cacheableTokens, promptTokens, rate)),
        };
    }

    /// <summary>诊断用分档行 (无副作用; 用户轮未知 ⇒ 显式声明档未知, 不猜)。</summary>
    public static string BandLine(int promptTokens, int cacheableTokens, int userTurnTokens)
    {
        var band = BandOf(userTurnTokens);
        if (userTurnTokens < 0)
            return $"分档: 用户轮长度未上报 ⇒ 档未知 (目标取红线 {Threshold:P0}; 禁按 0 冒充短档)";
        var prefix = cacheableTokens > 0 ? cacheableTokens : promptTokens;   // 口径: 与 KPI 分母同源 (需要命中面)
        var ceil = CeilingFor(prefix, userTurnTokens);
        var target = TargetFor(prefix, userTurnTokens);
        var need = PrefixTokensNeededForBand(userTurnTokens, Threshold);
        return $"分档: 用户轮 {userTurnTokens} tok ⇒ 档 {BandLabel(band)}({TurnBands[band].Lo}~{TurnBands[band].Hi}) "
             + $"结构上限 {ceil:P2} (prefix={prefix}) 目标 {target:P2} "
             + (target >= Threshold
                 ? $"达红线需前缀 ≥ {need:F0} token"
                 : $"该档结构性不可达红线 ⇒ 目标=上限 (达红线需前缀 ≥ {need:F0} token, 不可压用户轮)");
    }
}
