using System;
using System.Collections.Generic;

namespace agent.rag;


/// <summary>词法路: 字符二元组 Jaccard (无需向量, 因此旧维度残留文档仍可参与)。</summary>
public sealed class LexicalRoute : IRetrievalRoute
{
    public string Name => "lexical";

    public long Scored { get; private set; }

    public int[] Rank(QueryContext query, IReadOnlyList<RetrievalCandidate> candidates)
    {
        var n = candidates.Count;
        var ranks = new int[n];
        var scores = new double[n];
        var qgrams = FusionMath.CharacterBigrams(query.Text);
        var qset = new HashSet<string>(qgrams, StringComparer.Ordinal);
        for (var i = 0; i < n; i++)
        {
            scores[i] = FusionMath.Jaccard(qset, candidates[i].Bigrams);
            Scored++;
        }
        FusionMath.AssignRanks(scores, ranks);
        return ranks;
    }
}
