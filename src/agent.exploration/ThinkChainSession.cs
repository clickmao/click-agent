namespace agent.exploration;

/// <summary>思考链单步决策 (LLM 产出 — 宿主解析后注入; 本库不调 LLM)。</summary>
public sealed class ThinkStep
{
    /// <summary>本步假设/论断</summary>
    public string Hypothesis { get; set; } = string.Empty;
    /// <summary>决定探索的源 (空 = 准备收敛)</summary>
    public ExploreNode? NextExplore { get; set; }
    /// <summary>本步采纳的依据 (ThinkMemory 引用提升触发)</summary>
    public List<(string RecordId, string Ref)> Citations { get; set; } = new();
}

/// <summary>思考链收敛原因 (打点 think_converge.reason)。</summary>
public enum ConvergeReason
{
    MultiSourceAgreement,   // 多源一致
    BudgetExhausted,        // 预算/时限耗尽
    NoNewDiscoveries,       // 连续无新发现
    LlmSelfAssessed,        // LLM 自评依据充分
}

public sealed class ThinkChainResult
{
    public ConvergeReason Reason { get; set; }
    public int Steps { get; set; }
    public int SourcesUsed { get; set; }
    public double AvgConfidence { get; set; }
    public int WallMs { get; set; }
    public List<ExploreStepResult> Trail { get; set; } = new();
}

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

/// <summary>探索执行器抽象 (URL/文件/目录 — 宿主侧实现 IO; 本库禁直接 IO 依赖)。</summary>
public interface IExploreExecutor
{
    Task<ExploreStepResult> ExecuteAsync(ExploreNode node, CancellationToken ct = default);
}

internal static class ThinkNodeExtensions
{
    public static IReadOnlyList<(string RecordId, string Ref)> CitationsSafe(this ExploreNode node)
        => Array.Empty<(string, string)>(); // 引用由 ThinkStep.Citations 传入宿主后直接调 ThinkMemory — 节点不携带
}
