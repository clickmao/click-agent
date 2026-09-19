using System;
using System.Collections.Generic;

namespace agent.rag;

/// <summary>
/// 零依赖词法精排 (无模型基线)。双重身份: ① 精排段的默认可用实现; ② 精排增益的**负控** ——
/// 若它也把 NDCG 抬起来, 说明增益来自词面重合而非精排器本身, 不得据此宣称精排能力。
/// 打分 = coarseWeight × 粗排分 + (1 − coarseWeight) × 查询-文档 2-gram Jaccard (复用 FusionMath, 与词法路同式)。
/// </summary>
public sealed class LexicalRerankScorer : IRerankScorer
{
    private readonly double _coarseWeight;

    public LexicalRerankScorer(double coarseWeight = 0.5) => _coarseWeight = coarseWeight;

    public double Score(string query, string document, double coarseScore)
    {
        var qset = new HashSet<string>(FusionMath.CharacterBigrams(query ?? string.Empty), StringComparer.Ordinal);
        var dgrams = FusionMath.CharacterBigrams(document ?? string.Empty);
        var lex = FusionMath.Jaccard(qset, dgrams);
        return _coarseWeight * coarseScore + (1.0 - _coarseWeight) * lex;
    }
}
