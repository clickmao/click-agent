using System;
using System.Collections.Generic;

namespace agent.rag;

/// <summary>
/// 上下文精排度量 —— 纯函数, 零词表 (相关度分级由**外部真值**给出: 2=必需证据 / 1=相关 / 0=噪声)。
/// 位次折扣 log2(i+1) 与 IR 教材 / MTEB 同一口径; 排序类指标只做**诊断**, ship 判据仍是端到端答案质量。
/// 纪律: 单窗 = 噪声 ⇒ reps≥3 且报逐窗 + 极差; 跨窗禁相减。
/// </summary>
public static class RerankMetrics
{
    /// <summary>DCG@k = Σ (2^g_i − 1) / log2(i+1), i 从 1 起 (g_i ≤ 0 的位次贡献 0)。</summary>
    public static double Dcg(IReadOnlyList<int> gains, int k)
    {
        if (gains is null || k <= 0) return 0.0;
        var n = Math.Min(k, gains.Count);
        var s = 0.0;
        for (var i = 0; i < n; i++)
        {
            var g = gains[i];
            if (g <= 0) continue;
            s += (Math.Pow(2, g) - 1.0) / Math.Log2(i + 2);
        }
        return s;
    }

    /// <summary>NDCG@k = DCG@k / IDCG@k (理想序 = gains 降序); 分母为 0 记 0 (空序无增益可谈)。</summary>
    public static double NdcgAtK(IReadOnlyList<int> gains, int k)
    {
        var dcg = Dcg(gains, k);
        if (dcg == 0.0) return 0.0;
        var ideal = new List<int>(gains);
        ideal.Sort((a, b) => b.CompareTo(a));
        var idcg = Dcg(ideal, k);
        return idcg == 0.0 ? 0.0 : dcg / idcg;
    }

    /// <summary>MRR = 首个相关 (gain ≥ 1) 位次的倒数; 全噪声记 0。</summary>
    public static double Mrr(IReadOnlyList<int> gains)
    {
        if (gains is null) return 0.0;
        for (var i = 0; i < gains.Count; i++)
            if (gains[i] >= 1) return 1.0 / (i + 1);
        return 0.0;
    }

    /// <summary>Precision@k = 前 k 位中相关 (gain ≥ 1) 的占比; k 按实际长度截断。</summary>
    public static double PrecisionAtK(IReadOnlyList<int> gains, int k)
    {
        if (gains is null || k <= 0 || gains.Count == 0) return 0.0;
        var n = Math.Min(k, gains.Count);
        var rel = 0;
        for (var i = 0; i < n; i++)
            if (gains[i] >= 1) rel++;
        return (double)rel / n;
    }

    /// <summary>Recall@N (前置天花板, 不是精排指标): 必需证据的覆盖面 found/required; 无需覆盖时记 1。</summary>
    public static double RecallAtN(int required, int found)
    {
        if (required <= 0) return 1.0;
        var r = (double)found / required;
        return r < 0.0 ? 0.0 : (r > 1.0 ? 1.0 : r);
    }

    /// <summary>
    /// 一次精排读数 (四件套打包)。<paramref name="gainsInPromptOrder"/> = **实际进入 prompt 的顺序**对应的
    /// 相关度分级 (真值来源: 题面机械抽取的证据 ID + 分级标注)。
    /// </summary>
    public static RerankReading Measure(
        IReadOnlyList<int> gainsInPromptOrder, int k, int requiredEvidence, int foundEvidence)
    {
        var ndcg = NdcgAtK(gainsInPromptOrder, k);
        var mrr = Mrr(gainsInPromptOrder);
        var p = PrecisionAtK(gainsInPromptOrder, k);
        var r = RecallAtN(requiredEvidence, foundEvidence);
        var status = requiredEvidence > 0 && foundEvidence < requiredEvidence
            ? "召回不足(精排读数作废)"
            : "ok";
        return new RerankReading(ndcg, mrr, p, r, k, status);
    }
}
