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
        return Math.Round(hit.Value / (double)cacheableTokens, 4);
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
}
