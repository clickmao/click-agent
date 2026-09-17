using System;
using System.Collections.Generic;

namespace agent.rag;

/// <summary>
/// 融合召回编排: 候选池 → 各路名次 → RRF 分数 → 降序结果。
/// 单路可用时显式降级并计数 (绝不静默把单路当融合)。
/// </summary>
public sealed class FusionRecall
{
    private readonly FusionOptions _opt;
    private readonly RrfFuser _fuser;
    private readonly IRetrievalRoute? _dense;
    private readonly IRetrievalRoute? _lexical;

    public FusionRecall(FusionOptions options, IRetrievalRoute? dense = null, IRetrievalRoute? lexical = null)
    {
        _opt = options ?? new FusionOptions();
        _fuser = new RrfFuser(_opt.K0);
        _dense = dense;
        _lexical = lexical;
    }

    public FusionCounters Counters { get; } = new();

    /// <summary>返回按融合分降序的 (候选, 分数) 列表; 分数为原始 RRF 分 (未归一)。</summary>
    public List<KeyValuePair<RetrievalCandidate, double>> Rank(
        QueryContext query, IReadOnlyList<RetrievalCandidate> candidates)
    {
        var outList = new List<KeyValuePair<RetrievalCandidate, double>>(candidates.Count);
        if (candidates.Count == 0) return outList;

        var rankLists = new List<int[]>(2);
        var weights = new List<double>(2);

        var denseOk = _dense is not null;
        var lexOk = _lexical is not null;

        if (denseOk) rankLists.Add(_dense!.Rank(query, candidates));
        if (lexOk) rankLists.Add(_lexical!.Rank(query, candidates));

        if (rankLists.Count == 0) return outList;
        if (rankLists.Count == 1)
        {
            Counters.SingleRouteFallback++;
            weights.Add(denseOk ? _opt.DenseWeight : _opt.LexicalWeight);
        }
        else
        {
            weights.Add(_opt.DenseWeight);
            weights.Add(_opt.LexicalWeight);
        }

        Counters.FusionCalls++;
        if (denseOk) Counters.DenseUsed++;
        if (lexOk) Counters.LexicalUsed++;
        Counters.CandidatesScored += candidates.Count;

        var scores = _fuser.Scores(rankLists, weights, candidates.Count);
        var order = new int[candidates.Count];
        for (var i = 0; i < order.Length; i++) order[i] = i;
        Array.Sort(order, (a, b) =>
        {
            var c = scores[b].CompareTo(scores[a]);
            return c != 0 ? c : a.CompareTo(b);
        });
        for (var i = 0; i < order.Length; i++)
            outList.Add(new KeyValuePair<RetrievalCandidate, double>(candidates[order[i]], scores[order[i]]));
        return outList;
    }

    /// <summary>原始 RRF 分的理论满分 (归一化用)。</summary>
    public double MaxScore()
    {
        var w = new List<double>(2);
        if (_dense is not null) w.Add(_opt.DenseWeight);
        if (_lexical is not null) w.Add(_opt.LexicalWeight);
        return _fuser.MaxScore(w);
    }
}
