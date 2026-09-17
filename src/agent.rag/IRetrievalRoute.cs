using System;
using System.Collections.Generic;

namespace agent.rag;


/// <summary>可替换执行面端口: 一路检索对同一批候选给出 0 起名次 (与 eval/bge 的秩数组同口径)。</summary>
public interface IRetrievalRoute
{
    string Name { get; }

    /// <summary>返回长度 == candidates.Count 的秩数组; ranks[d] = 文档 d 的 0 起名次。</summary>
    int[] Rank(QueryContext query, IReadOnlyList<RetrievalCandidate> candidates);
}
