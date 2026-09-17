using System;
using System.Collections.Generic;

namespace agent.rag;


/// <summary>语义路: 查询向量 × 候选向量 余弦。维度不匹配的候选 (旧 512 维残留) 记 0 分并计数。</summary>
public sealed class DenseRoute : IRetrievalRoute
{
    public string Name => "dense";

    public long Scored { get; private set; }
    public long SkippedDimMismatch { get; private set; }

    public int[] Rank(QueryContext query, IReadOnlyList<RetrievalCandidate> candidates)
    {
        var n = candidates.Count;
        var ranks = new int[n];
        var scores = new double[n];
        var qv = query.Embedding;
        if (qv is null || qv.Length == 0)
        {
            for (var i = 0; i < n; i++) ranks[i] = i;   // 无查询向量 ⇒ 该路退化为文档序
            return ranks;
        }
        for (var i = 0; i < n; i++)
        {
            var dv = candidates[i].Embedding;
            if (dv is null || dv.Length != qv.Length)
            {
                scores[i] = double.NegativeInfinity;
                SkippedDimMismatch++;
                continue;
            }
            scores[i] = FusionMath.Cosine(qv, dv);
            Scored++;
        }
        FusionMath.AssignRanks(scores, ranks);
        return ranks;
    }
}
