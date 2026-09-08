namespace agent.exploration;

/// <summary>
/// v0.13.0 — 待探索源 (探索图节点)。
/// </summary>
public sealed class ExploreNode
{
    public ExploreSourceKind Kind { get; set; }
    /// <summary>引用: URL / 目录路径 / 文件路径 / 文本片段头 128ch</summary>
    public string Ref { get; set; } = string.Empty;
    /// <summary>发现来源 (null = 用户直接给出/种子)</summary>
    public string? DiscoveredFrom { get; set; }
    /// <summary>是否来自上下文 (用户例: 上下文内 URL > 上下文外目录)</summary>
    public bool FromContext { get; set; }
    public int Priority { get; set; }
    /// <summary>该节点已用步数 (渐进深入计数)</summary>
    public int StepsUsed { get; set; }
}

/// <summary>单步探索结果 (打点+回填思考链)。</summary>
public sealed class ExploreStepResult
{
    public bool Ok { get; set; }
    public ExploreSourceKind Kind { get; set; }
    public string Ref { get; set; } = string.Empty;
    public int StepN { get; set; }
    public int BudgetLeft { get; set; }
    public int Ms { get; set; }
    public long Bytes { get; set; }
    /// <summary>探索中发现的新源 (上下文含 URL / 网页含路径 / 目录含子项)</summary>
    public List<ExploreNode> Discovered { get; set; } = new();
    public string? Error { get; set; }
    /// <summary>内容摘要 (回填思考链, ≤400ch)</summary>
    public string Digest { get; set; } = string.Empty;
}

/// <summary>
/// v0.13.0 — 渐进式探索规划器: 优先级队列 + 每源预算 + 全局预算。
/// 纯逻辑 (无 IO), 单测覆盖: 优先级序 (上下文内 URL &gt; 上下文外目录 — 用户钦定例)、
/// 预算耗尽、去重、发现链。
/// </summary>
public sealed class ExplorationPlanner
{
    private readonly ExplorationConfig _config;
    private readonly List<ExploreStepResult> _history = new();
    private readonly HashSet<string> _seen = new(StringComparer.OrdinalIgnoreCase);

    public ExplorationPlanner(ExplorationConfig? config = null)
        => _config = config ?? new ExplorationConfig();

    /// <summary>全局已用步数</summary>
    public int TotalStepsUsed { get; private set; }

    /// <summary>全局预算耗尽</summary>
    public bool BudgetExhausted => TotalStepsUsed >= _config.MaxTotalSteps;

    private readonly PriorityQueue<ExploreNode, int> _queue = new();

    /// <summary>种子源入队 (用户/上下文直接给出)。</summary>
    public void Seed(ExploreSourceKind kind, string reference, bool fromContext, string? discoveredFrom = null)
    {
        var key = NodeKey(kind, reference);
        if (string.IsNullOrWhiteSpace(reference) || !_seen.Add(key)) return;
        _queue.Enqueue(new ExploreNode
        {
            Kind = kind,
            Ref = reference.Trim(),
            FromContext = fromContext,
            DiscoveredFrom = discoveredFrom,
            Priority = _config.GetPriority(kind, fromContext),
        }, _config.GetPriority(kind, fromContext));
    }

    /// <summary>取下一步 (优先级最小者; 预算校验: 全局 + 该源 per-ref 计数)。</summary>
    public ExploreNode? TryDequeueNext()
    {
        if (BudgetExhausted) return null;
        while (_queue.TryDequeue(out var node, out _))
        {
            // per-ref 预算 (同 ref 渐进深入上限):
            if (node.StepsUsed >= _config.GetBudget(node.Kind)) continue;
            return node;
        }
        return null;
    }

    /// <summary>节点再入队 (渐进深入: 该 ref 预算未耗尽且发现了新内容)。</summary>
    public void Requeue(ExploreNode node)
    {
        node.StepsUsed++;
        if (node.StepsUsed < _config.GetBudget(node.Kind))
            _queue.Enqueue(node, node.Priority + node.StepsUsed); // 深入加罚 — 广度优先倾向
    }

    /// <summary>记录一步结果 (历史+全局计数+发现源自动入队)。</summary>
    public IReadOnlyList<ExploreNode> Record(ExploreStepResult result, ExploreNode source)
    {
        TotalStepsUsed++;
        _history.Add(result);
        var enqueued = new List<ExploreNode>();
        foreach (var d in result.Discovered)
        {
            var key = NodeKey(d.Kind, d.Ref);
            if (!_seen.Add(key)) continue;
            d.Priority = _config.GetPriority(d.Kind, d.FromContext);
            _queue.Enqueue(d, d.Priority);
            enqueued.Add(d);
        }
        return enqueued;
    }

    public IReadOnlyList<ExploreStepResult> History => _history;

    public IReadOnlyCollection<ExploreNode> PendingSnapshot
    {
        get
        {
            // 快照不改队列: 逐个出再入 (PriorityQueue 无枚举器)
            var list = new List<ExploreNode>();
            var items = new List<(ExploreNode n, int p)>();
            while (_queue.TryDequeue(out var n, out var p)) items.Add((n, p));
            foreach (var (n, p) in items) { list.Add(n); _queue.Enqueue(n, p); }
            return list;
        }
    }

    private static string NodeKey(ExploreSourceKind kind, string reference) =>
        $"{kind}:{reference.Trim().TrimEnd('/').ToLowerInvariant()}";
}
