namespace agent.exploration;

/// <summary>
/// 粘性路由记忆: 双门判定 = embedding 相似 ≥ 阈值 **且** 意图一致 **且** 实体指纹一致。
/// 实体指纹 (URL/路径) 是"形近意远"防线 — "总结 https://a.com" 与 "总结 https://b.com"
/// 意图相同但指纹不同 = 不同任务, 不得粘 (跑测反向样本 T-R02)。
/// </summary>
public sealed class StickyRouteMemory
{
    private readonly StickyRouteConfig _config;
    private readonly List<RouteRecord> _records = new();
    private readonly object _lock = new();

    public StickyRouteMemory(StickyRouteConfig? config = null) => _config = config ?? new StickyRouteConfig();

    public int Count { get { lock (_lock) return _records.Count; } }

    public void Write(RouteRecord record)
    {
        lock (_lock) _records.Add(record);
    }

    /// <summary>
    /// 路由决策: 相似+意图+实体指纹三重一致 → sticky (首用成功模型) / avoid (已知失败模型)。
    /// 多命中取最近成功 (时间近者优先 — 环境变化后旧结论过期)。
    /// </summary>
    public StickyRouteDecision Decide(string questionEmbeddingSource, float[]? embedding, string intent, string entityFingerprint, DateTime utcNow)
    {
        var d = new StickyRouteDecision();
        if (!_config.Enabled || embedding is null || embedding.Length == 0) return d;
        lock (_lock)
        {
            RouteRecord? bestSuccess = null, bestFail = null;
            var bestS = 0.0;
            var bestRank = (sim: 0.0, ts: DateTime.MinValue);
            foreach (var r in _records)
            {
                if (r.QuestionEmbedding is null) continue;
                if (!string.Equals(r.Intent, intent, StringComparison.OrdinalIgnoreCase)) continue; // 门2: 意图
                if (!string.Equals(r.EntityFingerprint, entityFingerprint, StringComparison.Ordinal)) continue; // 门3: 实体
                if ((utcNow - r.CreatedAtUtc).TotalHours > _config.StickyTtlHours) continue; // TTL
                var sim = Cosine(embedding, r.QuestionEmbedding);
                if (sim < _config.SimilarityThreshold) continue; // 门1: 相似
                // 排序: 相似度为主, 差 < 0.01 视为同分 (embedding 抖动容差) → 取最近
                // (环境变化后旧结论过期 — "最近成功优先", 真机 sim 抖动实证驱动):
                if (sim > bestRank.sim + 0.01
                    || (sim > bestRank.sim - 0.01 && r.CreatedAtUtc > bestRank.ts))
                {
                    bestRank = (sim: sim, ts: r.CreatedAtUtc);
                    bestS = sim;
                    if (r.Outcome == "success") bestSuccess = r;
                    else bestFail = r;
                }
            }
            if (bestSuccess is not null)
            {
                bestSuccess.HitCount++;
                d.Sticky = true;
                d.ModelId = bestSuccess.ModelId;
                d.Similarity = Math.Round(bestS, 4);
                d.Reason = $"sticky_hit (sim={bestS:F2}, hits={bestSuccess.HitCount})";
            }
            else if (bestFail is not null)
            {
                d.Avoid = true;
                d.ModelId = bestFail.ModelId;
                d.Similarity = Math.Round(bestS, 4);
                d.Reason = $"sticky_avoid (已知失败模型, sim={bestS:F2})";
            }
        }
        return d;
    }

    private static double Cosine(float[] a, float[] b)
    {
        if (a.Length != b.Length || a.Length == 0) return 0;
        double dot = 0, na = 0, nb = 0;
        for (var i = 0; i < a.Length; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
        return na == 0 || nb == 0 ? 0 : dot / (Math.Sqrt(na) * Math.Sqrt(nb));
    }
}
