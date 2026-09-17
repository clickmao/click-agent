using System;
using System.Collections.Generic;

namespace agent.rag;


/// <summary>RRF 融合器: score[d] = Σ_r w_r / (k0 + rank_r[d] + 1) (与 eval/bge 冻结算术同式)。</summary>
public sealed class RrfFuser
{
    private readonly int _k0;

    public RrfFuser(int k0) => _k0 = k0;

    public double[] Scores(IReadOnlyList<int[]> rankLists, IReadOnlyList<double> weights, int candidateCount)
    {
        var scores = new double[candidateCount];
        for (var r = 0; r < rankLists.Count; r++)
        {
            var w = weights[r];
            var rl = rankLists[r];
            for (var d = 0; d < candidateCount; d++)
                scores[d] += w / (_k0 + rl[d] + 1);
        }
        return scores;
    }

    /// <summary>理论满分 (所有路都排第 0) —— 用于把分数线性归一到 0..1, 以便与既有阈值口径共存。</summary>
    public double MaxScore(IReadOnlyList<double> weights)
    {
        var m = 0.0;
        for (var r = 0; r < weights.Count; r++) m += weights[r] / (_k0 + 1);
        return m;
    }
}
