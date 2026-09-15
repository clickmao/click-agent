namespace agent.modelqueue;

/// <summary>
/// R377 (用户钦定): **prompt 缓存命中率纳入优化 KPI**。
///
/// 语义: 模型 API 的 usage 里带 `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens`
///       (DeepSeek 等 OpenAI 兼容提供方)。
///
/// R380 (用户钦定 **口径修订**, 首要 KPI): 命中率**只算「需要命中的部分」** ——
///   本轮新增内容不计入分母 (新增是首次发送, 必然不可能命中, 计入即稀释指标、
///   把"前缀被正确复用"与"本轮本来就要新发"混为一谈)。
///   有效命中率 = hit / min(本轮 prompt, 上一轮已发 prompt)
///   会话首轮没有"需要命中"的部分 → 记 <see cref="Unknown"/> (-1, 不适用, 不并入比率)。
///   参考值 (旧口径 hit/(hit+miss)) 仍打点, 但**不作判定口径**。
///
/// 铁律 (与"诚实边界"一致):
///   ① **未上报 ≠ 0 命中** —— provider 没给字段时记 <see cref="Unknown"/> (-1), 不得用 0 冒充,
///      否则"没测到"会被读成"命中率 0%" (判定空心)。
///   ② 分母为 0 (hit=miss=0 或缺一项/首轮) 同样记 -1: 没有数据就没有比率。
///   ③ 打点字段名固定 `cache_hit_tokens` / `cache_miss_tokens` / `cache_hit_rate` /
///      `cacheable_tokens` / `effective_hit_rate`, 便于离线聚合 (scripts/kpi_cache_hit.py)。
/// </summary>
public static class PromptCacheKpi
{
    /// <summary>未上报/无分母的统一哨兵值 (int 与 double 共用语义)。</summary>
    public const int Unknown = -1;

    public static int HitTokens(int? hit) => hit ?? Unknown;

    public static int MissTokens(int? miss) => miss ?? Unknown;

    /// <summary>旧口径 (参考值): hit / (hit + miss), 保留 4 位; 未上报或无分母 → -1。</summary>
    public static double HitRate(int? hit, int? miss)
    {
        if (hit is null || miss is null) return Unknown;
        var total = hit.Value + miss.Value;
        if (total <= 0) return Unknown;
        return Math.Round(hit.Value / (double)total, 4);
    }

    /// <summary>
    /// R380 口径: 「需要命中的 token 数」= min(本轮 prompt, 上一轮已发 prompt)。
    /// 上一轮无记录 (=0, 会话首轮/进程内首次) → 0 表示不适用。
    /// 取 min 的原因: prompt 缩短时 (截断/修复轮) 不可能命中超过自身长度, 否则比率 &gt;1 失真。
    /// </summary>
    public static int CacheableTokens(int promptTokens, int lastPromptTokens)
        => lastPromptTokens <= 0 ? 0 : Math.Min(promptTokens, lastPromptTokens);

    /// <summary>
    /// R380 有效命中率 = hit / cacheable, 保留 4 位。
    /// cacheable ≤ 0 (会话首轮) 或 **未上报** (null/-1) → -1 (不适用; 未上报绝不冒充 0 命中)。
    /// </summary>
    public static double EffectiveHitRate(int? hit, int cacheableTokens)
    {
        if (cacheableTokens <= 0) return Unknown;
        if (hit is null || hit.Value < 0) return Unknown;   // 未上报 → 不适用 (机检 PromptCacheRedlineTests 覆盖)
        // R475: 命中量 > 可缓存上界 **在物理上不可能** (超出部分只可能来自比同会话上一轮更长的共享前缀)。
        // 保留 >1 会直接污染红线统计 (R474 实测 hit=2,944 > cacheable=2,900 ⇒ 1.0152) ⇒ 该轮不适用 K2b,
        // 归因交 shared_prefix 通道 (见 ExceedsSameSession / Channel) —— 禁用 min() 掩盖, 也禁静默 0。
        if (hit.Value > cacheableTokens) return Unknown;
        return Math.Round(hit.Value / (double)cacheableTokens, 4);
    }

    /// <summary>
    /// R475: 该轮命中量是否**超出同会话可复用上界** (min(prompt, 上一轮 prompt))。
    /// 成立 ⇒ 命中不可能来自同会话前缀复用 (只可能来自更长的跨会话共享前缀/同文本缓存)
    ///   ⇒ 归 `shared_prefix` 通道、`effective_hit_rate` 置 -1 (不适用), 防 >1 污染红线。
    /// 单源: Channel / SharedPrefixHitTokens / SharedPrefixHitRate 共用本判据, 禁各处各写。
    /// </summary>
    public static bool ExceedsSameSession(int? hit, int promptTokens, int lastPromptTokens)
    {
        if (hit is null || hit.Value <= 0 || lastPromptTokens <= 0) return false;
        return hit.Value > Math.Min(promptTokens, lastPromptTokens);
    }

    /// <summary>
    /// 缓存单元 (token)。提供方按单元落盘; **真机实测规律** (mt_fix4): 命中 = (floor(前缀/64) − 1) × 64
    ///  —— 即前缀最后一个完整单元不计入命中 (落盘时机=用户输入结束位置的副作用), 外加末单元残缺损耗。
    /// </summary>
    public const int CacheUnitTokens = 64;

    /// <summary>给定已发前缀, 该前缀**理论上可达的命中上限** (单元边界 + 末单元损耗已计入)。</summary>
    public static int HitCeiling(int prefixTokens)
    {
        var units = prefixTokens / CacheUnitTokens;
        return units <= 1 ? 0 : (units - 1) * CacheUnitTokens;
    }

    /// <summary>
    /// 达到 <paramref name="target"/> 比值所需的**最小前缀 token 数** (按**最坏对齐**取界, 不是理想界)。
    /// 推导: 命中上限 = (floor(P/64) − 1) × 64 ⇒ 前缀落在单元带 [n, n+1) 内时最坏 = (n−1)/(n+1) ≥ target
    ///   ⇒ n ≥ (1+target)/(1−target)  ⇒ **97% 需 n=66 (4224 token, 当前红线)**; 95% 需 n=39 (2496); 98% 需 n=99 (6336); 90% 需 n=19 (1216)。
    /// 直觉: 每个请求边界固定损耗"1 整单元 + 1 残单元", 前缀越厚损耗占比越小 → 高红线必然要求前缀加厚。
    /// (实测校验: 前缀 2001 → 上限 1920 = 95.95%; 2428 → 2304 = 94.90% ✓ 与公式一致)
    /// </summary>
    public static int PrefixTokensNeededFor(double target)
    {
        if (target <= 0 || target >= 1) return 0;
        // 先归一 (6 位小数) 再取整: 否则浮点噪声会把稳健界多算一个 64-token 单元
        // (真机: 0.90 → 1.9/0.1 = 19.000000000000004 → Ceiling 得 20 单元 = 1280, 正确值 19 单元 = 1216)
        var n = (int)Math.Ceiling(Math.Round((1.0 + target) / (1.0 - target), 6));
        return n * CacheUnitTokens;
    }

    /// <summary>打点字段 (顺序固定: hit / miss / rate), 直接铺进 telemetry 的 params 元组数组。</summary>
    public static (string Key, object? Value)[] Fields(int? hit, int? miss) => new (string, object?)[]
    {
        ("cache_hit_tokens", HitTokens(hit)),
        ("cache_miss_tokens", MissTokens(miss)),
        ("cache_hit_rate", HitRate(hit, miss)),
    };

    /// <summary>R380 口径字段 (首要 KPI 判定用): cacheable_tokens + effective_hit_rate。</summary>
    public static (string Key, object? Value)[] EffectiveFields(int? hit, int promptTokens, int lastPromptTokens) => new (string, object?)[]
    {
        ("cacheable_tokens", CacheableTokens(promptTokens, lastPromptTokens)),
        ("effective_hit_rate", EffectiveHitRate(hit, CacheableTokens(promptTokens, lastPromptTokens))),
    };

    /// <summary>
    /// R470: 命中**归因通道**。机检真实远端遥测 (`data/telemetry/host.jsonl`, 43 条 `llm_call`) 的结论:
    /// `effective_hit_rate` **43/43 = -1** (全部无同会话前驱 ⇒ 真实流量几乎全是「每会话一次调用」),
    /// 而提供方侧**确实命中** 2,048~2,304 tok (32/43 命中 &gt; 0, 64-token 单元对齐)
    /// ⇒ 既有 K2b 通道对**真实流量结构性不可测**: 收益客观存在却无度量、无驱动信号。
    ///
    /// 本通道**只增不改**: 既有 `cacheable_tokens` / `effective_hit_rate` 与红线阈值一字不动。
    /// 语义 (last = 同会话上一轮已发 prompt, 无记录 = 0):
    ///   `same_session`  : last &gt; 0            —— 会话内前缀复用 (R380 既定区间);
    ///   `shared_prefix` : last == 0 ∧ prompt &gt; 0 —— 无同会话前驱 ⇒ 命中只可能来自**跨会话共享前缀**
    ///                     (含提供方同文本缓存; 二者同 token 数下不可分 ⇒ 因果不在本字段声明内);
    ///   `unknown`       : prompt == 0          —— 无数据。
    /// </summary>
    public static string Channel(int promptTokens, int lastPromptTokens, int? hit = null)
        => promptTokens <= 0 ? "unknown"
            : (lastPromptTokens > 0 && !ExceedsSameSession(hit, promptTokens, lastPromptTokens) ? "same_session" : "shared_prefix");

    /// <summary>跨会话共享前缀通道的命中 token (**仅该通道**; 其余通道 -1 ⇒ 禁双计; 未上报 -1, 不得冒充 0)。</summary>
    public static int SharedPrefixHitTokens(int? hit, int promptTokens, int lastPromptTokens)
    {
        if (promptTokens <= 0) return Unknown;
        if (lastPromptTokens > 0 && !ExceedsSameSession(hit, promptTokens, lastPromptTokens)) return Unknown;
        return HitTokens(hit);
    }

    /// <summary>跨会话共享前缀通道的命中占比 = hit/(hit+miss) (**仅该通道**; 其余通道/无分母/未上报 → -1)。</summary>
    public static double SharedPrefixHitRate(int? hit, int? miss, int promptTokens, int lastPromptTokens)
    {
        if (promptTokens <= 0) return Unknown;
        if (lastPromptTokens > 0 && !ExceedsSameSession(hit, promptTokens, lastPromptTokens)) return Unknown;
        return HitRate(hit, miss);
    }

    /// <summary>R470 通道字段 (顺序固定): channel + 该通道命中量 + 该通道命中占比。R475: 逐字段传 hit (超同会话上界 ⇒ 归共享前缀通道)。</summary>
    public static (string Key, object? Value)[] ChannelFields(int? hit, int? miss, int promptTokens, int lastPromptTokens) => new (string, object?)[]
    {
        ("cache_channel", Channel(promptTokens, lastPromptTokens, hit)),
        ("shared_prefix_hit_tokens", SharedPrefixHitTokens(hit, promptTokens, lastPromptTokens)),
        ("shared_prefix_hit_rate", SharedPrefixHitRate(hit, miss, promptTokens, lastPromptTokens)),
    };
}
