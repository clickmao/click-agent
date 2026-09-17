namespace agent.exploration;

/// <summary>
/// v0.13.0 T3 M-C — 思考链会话 (渐进探索 + 依据评估 + 收敛判定 + 记忆读写)。
/// 宿主侧每轮: DecideStep (LLM) → ExecuteStep (探索执行器) → Evaluate → 收敛判据。
/// </summary>
public sealed class ThinkChainSession
{
    private readonly ExplorationPlanner _planner;
    private readonly ThinkMemory? _memory;
    private readonly DateTime _deadlineUtc;
    private int _staleRounds; // 连续无新发现轮数

    public ThinkChainSession(ExplorationPlanner planner, ThinkMemory? memory, int deadlineMs)
    {
        _planner = planner;
        _memory = memory;
        _deadlineUtc = DateTime.UtcNow.AddMilliseconds(deadlineMs);
    }

    public IReadOnlyList<ThinkMemoryHit> SeedFromMemory(float[] questionEmbedding, int topK = 3) =>
        _memory?.Recall(questionEmbedding, topK) ?? Array.Empty<ThinkMemoryHit>();

    /// <summary>执行一步 (探索节点已由 LLM 决定); 返回 null = 无步可走 (应收敛)。</summary>
    public async Task<ExploreStepResult?> ExecuteStepAsync(ExploreNode node, IExploreExecutor executor, CancellationToken ct = default)
    {
        var result = await executor.ExecuteAsync(node, ct).ConfigureAwait(false);
        _planner.Record(result, node);
        if (result.Discovered.Count == 0) _staleRounds++;
        else _staleRounds = 0;
        if (result.Ok && _memory is not null)
            foreach (var c in node.CitationsSafe())
                _memory.ApplyCitationBoost(c.RecordId, c.Ref);
        return result;
    }

    /// <summary>收敛判据 (用户钦定 §1.4; 任一满足即收敛)。</summary>
    public ThinkChainResult EvaluateConvergence(IReadOnlyList<EvidenceItem> supporting, int steps, int wallMs, bool llmSelfAssessed)
    {
        var reason = ConvergeReason.LlmSelfAssessed;
        if (llmSelfAssessed) reason = ConvergeReason.LlmSelfAssessed;
        else if (_planner.BudgetExhausted || DateTime.UtcNow >= _deadlineUtc) reason = ConvergeReason.BudgetExhausted;
        else if (_staleRounds >= 2) reason = ConvergeReason.NoNewDiscoveries;
        else if (EvidenceScorer.Score(supporting) >= EvidenceScorer.HighThreshold) reason = ConvergeReason.MultiSourceAgreement;
        return new ThinkChainResult
        {
            Reason = reason,
            Steps = steps,
            SourcesUsed = supporting.Select(e => e.Domain).Distinct(StringComparer.OrdinalIgnoreCase).Count(),
            AvgConfidence = EvidenceScorer.Score(supporting),
            WallMs = wallMs,
        };
    }
}
