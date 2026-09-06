namespace agent.modelqueue;

/// <summary>调用通道 (需求1: 优先级 本地 &gt; 官方 &gt; 远端 API)</summary>
public enum ModelChannel
{
    Local,
    Official,
    Remote,
}

/// <summary>通道运行时状态 (并发计数 + 可用性)</summary>
public sealed class ChannelState
{
    public ModelChannel Channel { get; init; }
    public int Running { get; set; }

    /// <summary>通道可用 (本地=模型就绪; 官方=key 已注入; 远端=目录非空)</summary>
    public bool Available { get; set; }
}

/// <summary>
/// 通道调度器 (需求1 核心落地): 三通道并发数托管 — 任意通道未达并发上限即可继续接任务;
/// 分派优先级恒为 本地 &gt; 官方 &gt; 远端; 子任务按 并发余量×推理能力×推理速度×价格 综合打分选模。
/// 全部阈值走配置 (并发数/速度权重), 零硬编码。
/// </summary>
public sealed class ChannelScheduler
{
    private readonly object _lock = new();
    private readonly Dictionary<ModelChannel, ChannelState> _channels = new();

    private readonly int _localMaxConcurrency;
    private readonly int _officialMaxConcurrency;
    private readonly int _remoteMaxConcurrency;

    /// <summary>综合打分权重 (推理能力 0.4 / 速度 0.3 / 价格 0.3 — 可调, 走配置则由调用方传入)</summary>
    public double ReasoningWeight { get; set; } = 0.4;
    public double SpeedWeight { get; set; } = 0.3;
    public double PriceWeight { get; set; } = 0.3;

    /// <summary>
    /// v0.11.0 R15: 余额判定服务 (可选, 由宿主装配后赋值)。
    /// EstimateBalance.Sufficient=false 的模型在排序中强降权 — auto 主路径不再选余额不足的模型。
    /// </summary>
    public Func<string, int, (double? Remaining, bool Sufficient)>? BalanceProbe { get; set; }

    public ChannelScheduler(int localMax = 2, int officialMax = 4, int remoteMax = 4)
    {
        _localMaxConcurrency = localMax;
        _officialMaxConcurrency = officialMax;
        _remoteMaxConcurrency = remoteMax;
        _channels = new Dictionary<ModelChannel, ChannelState>
        {
            [ModelChannel.Local] = new() { Channel = ModelChannel.Local, Available = true },
            [ModelChannel.Official] = new() { Channel = ModelChannel.Official, Available = false },
            [ModelChannel.Remote] = new() { Channel = ModelChannel.Remote, Available = true },
        };
    }

    /// <summary>通道可用性外部刷新 (官方 key 注入/撤销, 本地模型就绪状态)</summary>
    public void SetAvailable(ModelChannel channel, bool available)
    {
        lock (_lock)
            _channels[channel].Available = available;
    }

    /// <summary>通道是否有并发余量且可用 (优先级顺序遍历)</summary>
    public ModelChannel? AcquireChannel()
    {
        lock (_lock)
        {
            foreach (var (channel, max) in new[]
                     {
                         (ModelChannel.Local, _localMaxConcurrency),
                         (ModelChannel.Official, _officialMaxConcurrency),
                         (ModelChannel.Remote, _remoteMaxConcurrency),
                     })
            {
                var state = _channels[channel];
                if (state.Available && state.Running < max)
                {
                    state.Running++;
                    return channel;
                }
            }
            return null; // 全通道满
        }
    }

    /// <summary>释放通道并发槽</summary>
    public void ReleaseChannel(ModelChannel channel)
    {
        lock (_lock)
        {
            var state = _channels[channel];
            if (state.Running > 0)
                state.Running--;
        }
    }

    /// <summary>通道快照 (/status 可读)</summary>
    public IReadOnlyList<ChannelState> Snapshot()
    {
        lock (_lock)
            return _channels.Values.OrderBy(c => c.Channel).ToList();
    }

    /// <summary>
    /// 子任务综合选模 (需求1 ⑤): 按通道余量 × 推理能力 × 推理速度(代理: 价格越低通常越快的轻模型偏好,
    /// 以 suited_for 含 "chat/summary/classify" 记高速) × 价格 打分; 候选 = 指定通道的模型集合
    /// (本地通道由调用方传本地模型描述; 官方=OfficialModels; 远端=目录)。
    /// 返回排序后的候选 (首=最优)。低速任务需求 (planning/reasoning) 偏好高推理分。
    /// </summary>
    public IReadOnlyList<ScoredCandidate> RankCandidates(
        IReadOnlyList<ModelCatalogEntry> candidates, TaskKindHint kind, int estimatedTokens)
    {
        var ranked = new List<ScoredCandidate>();
        var speedFirstKind = kind is TaskKindHint.KeywordTagging or TaskKindHint.IntentClassification
                         or TaskKindHint.ContextCompression or TaskKindHint.TendencyAnalysis;
        foreach (var m in candidates)
        {
            // 价格分: 输入+输出混合均价 → 越低分越高 (归一 0-1, 以 10 USD/M 为上限)
            var avgPrice = (m.PriceInPerM + m.PriceOutPerM) / 2;
            var priceScore = 1.0 - Math.Min(1.0, avgPrice / 10.0);

            // v0.11.0 (打点驱动修复): key 未配置的模型不可用 → 强降权 (打点实测曾选 gpt-4o-mini 而其 env 缺失)
            // official 通道由 OfficialKeys 统一供 key, 不按 env 判
            if (m.Provider != "official" &&
                string.IsNullOrEmpty(Environment.GetEnvironmentVariable(m.ApiKeyEnv)))
            {
                priceScore = 0; // 无 key = 无法调用, 排序沉底 (不删除: 留给显式 /model 指定)
            }

            // v0.11.0 R15: 余额不足 (换算后低于判定线) → 同样强降权 (auto 不选将失败的模型)
            if (BalanceProbe is not null)
            {
                var est = BalanceProbe(m.Provider, estimatedTokens);
                if (!est.Sufficient)
                    priceScore = 0;
            }

            // 速度分: 轻模型偏好 (suited_for 含轻任务标签 + 价格低即快)
            var isSpeedy = m.SuitedFor.Any(s => s is "chat" or "summary" or "classify");
            var speedScore = isSpeedy ? 1.0 : priceScore * 0.8;

            var reasoningScore = m.ReasoningScore / 10.0;
            var wR = speedFirstKind ? ReasoningWeight * 0.5 : ReasoningWeight;
            var wS = speedFirstKind ? SpeedWeight * 1.5 : SpeedWeight;
            var wP = PriceWeight;
            var total = wR * reasoningScore + wS * speedScore + wP * priceScore;

            ranked.Add(new ScoredCandidate
            {
                Model = m,
                TotalScore = Math.Round(total, 4),
                PriceScore = Math.Round(priceScore, 4),
                SpeedScore = Math.Round(speedScore, 4),
                ReasoningScore = Math.Round(reasoningScore, 4),
            });
        }
        return ranked.OrderByDescending(r => r.TotalScore).ToList();
    }
}

/// <summary>选模打分结果 (审计/调试 — LastSelectionBasis 落此)</summary>
public sealed class ScoredCandidate
{
    public ModelCatalogEntry Model { get; init; } = null!;
    public double TotalScore { get; init; }
    public double PriceScore { get; init; }
    public double SpeedScore { get; init; }
    public double ReasoningScore { get; init; }
}
