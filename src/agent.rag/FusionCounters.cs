using System;
using System.Collections.Generic;

namespace agent.rag;


/// <summary>融合路数打点 (证据: 每路真实被用次数 + 降级/跳过次数 —— 防"空心端口")。</summary>
public sealed class FusionCounters
{
    public long FusionCalls;
    public long DenseUsed;
    public long LexicalUsed;
    public long SingleRouteFallback;
    public long DimMismatchSkipped;
    public long CandidatesScored;
    public long BigramMemoHits;

    public void Reset()
    {
        FusionCalls = DenseUsed = LexicalUsed = SingleRouteFallback = 0;
        DimMismatchSkipped = CandidatesScored = BigramMemoHits = 0;
    }
}
