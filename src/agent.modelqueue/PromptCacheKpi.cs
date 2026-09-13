namespace agent.modelqueue;

/// <summary>
/// R377 (用户钦定): **prompt 缓存命中率纳入优化 KPI**。
///
/// 语义: 模型 API 的 usage 里带 `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens`
///       (DeepSeek 等 OpenAI 兼容提供方), 二者构成命中率 = hit / (hit + miss)。
///       命中率是**成本侧 KPI**(归入 token 使用量): 高命中 = 可复用前缀被真复用, 同题 token 成本下降。
///
/// 铁律 (与"诚实边界"一致):
///   ① **未上报 ≠ 0 命中** —— provider 没给字段时记 <see cref="Unknown"/> (-1), 不得用 0 冒充,
///      否则"没测到"会被读成"命中率 0%" (判定空心)。
///   ② 分母为 0 (hit=miss=0 或缺一项) 同样记 -1: 没有数据就没有比率。
///   ③ 打点字段名固定 `cache_hit_tokens` / `cache_miss_tokens` / `cache_hit_rate`,
///      便于离线聚合 (scripts/kpi_cache_hit.py) 与其他 KPI 同表对比。
/// </summary>
public static class PromptCacheKpi
{
    /// <summary>未上报/无分母的统一哨兵值 (int 与 double 共用语义)。</summary>
    public const int Unknown = -1;

    public static int HitTokens(int? hit) => hit ?? Unknown;

    public static int MissTokens(int? miss) => miss ?? Unknown;

    /// <summary>命中率 ∈ [0,1], 保留 4 位; 未上报或无分母 → -1。</summary>
    public static double HitRate(int? hit, int? miss)
    {
        if (hit is null || miss is null) return Unknown;
        var total = hit.Value + miss.Value;
        if (total <= 0) return Unknown;
        return Math.Round(hit.Value / (double)total, 4);
    }

    /// <summary>打点字段 (顺序固定: hit / miss / rate), 直接铺进 telemetry 的 params 元组数组。</summary>
    public static (string Key, object? Value)[] Fields(int? hit, int? miss) => new (string, object?)[]
    {
        ("cache_hit_tokens", HitTokens(hit)),
        ("cache_miss_tokens", MissTokens(miss)),
        ("cache_hit_rate", HitRate(hit, miss)),
    };
}
