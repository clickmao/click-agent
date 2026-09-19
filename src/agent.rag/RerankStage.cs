using System;
using System.Collections.Generic;

namespace agent.rag;

/// <summary>
/// 精排段 (漏斗: 召回 → 粗排 → **精排** → 装配 的第二级)。职责 = 对**已召回池**重排序, 把相关度高的
/// 候选顶进 prompt 预算窗口头部。铁律: ① 不扩召回; ② 排序确定 (同分按入参索引升序, 稳定);
/// ③ 精排产物只作用在 prompt 的可变区, 恒前缀不受影响 (前缀命中率 ≥97% 不得破)。
/// </summary>
public static class RerankStage
{
    public static RerankCandidate[] Order(IReadOnlyList<RerankCandidate> pool, string query, IRerankScorer scorer)
    {
        var idx = OrderIndices(pool, query, scorer);
        var outp = new RerankCandidate[idx.Length];
        for (var i = 0; i < idx.Length; i++) outp[i] = pool[idx[i]];
        return outp;
    }

    /// <summary>同 <see cref="Order"/> 的索引形态 (供调用方按原索引映射回自有类型, 避免 Id 撞车)。</summary>
    public static int[] OrderIndices(IReadOnlyList<RerankCandidate> pool, string query, IRerankScorer scorer)
    {
        if (pool is null || pool.Count == 0) return Array.Empty<int>();
        var n = pool.Count;
        var scores = new double[n];
        var idx = new int[n];
        for (var i = 0; i < n; i++)
        {
            scores[i] = scorer.Score(query, pool[i].Content, pool[i].CoarseScore);
            idx[i] = i;
        }
        Array.Sort(idx, (a, b) =>
        {
            var c = scores[b].CompareTo(scores[a]);
            return c != 0 ? c : a.CompareTo(b);
        });
        return idx;
    }
}
