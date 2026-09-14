namespace agent.llamacpp;

/// <summary>
/// R412: <b>会话级账本</b>（本地生成端）—— 把「上一轮总长 / 上一轮生成」按 <c>sessionKey</c> 分开记账。
///
/// 为什么必须分桶（R412 代码事实 §1.3）:
/// <see cref="LlamaCppTextGenerator"/> 的 <c>LastPromptTokens</c>/<c>LastGeneratedTokens</c> 是**实例级唯一**的，
/// 而长驻端口按设计是**进程内单例**（一个 server 服务所有会话）。多会话交替或并发时:
///   • A 会话刚写完、B 会话立刻覆盖 ⇒ A 下一轮读到的「上一轮」是**别人的** ⇒
///     交给 K2b 台账的 <c>carryOverCeiling</c> 被污染，判红/判绿都可能失真（且从外部看不出来）；
///   • 分母错了 ⇒ 复用率 > 1 或异常偏低，正是「口径错」的机检特征。
/// 分桶后 ceiling 只由**本会话自己**的上一轮决定；无 <c>sessionKey</c> 时退回实例级（兼容无会话形态）。
///
/// 端口化纪律: 纯内存、零 I/O、零 llama.cpp 类型依赖 ⇒ 可单测、可替换；
/// 被使用计数: <see cref="TrackedSessions"/> / <see cref="ConcurrentTurns"/> /
/// <see cref="MaxConcurrentTurns"/> / <see cref="UnkeyedTurns"/>。
/// </summary>
public sealed class LocalSessionTracker
{
    /// <summary>会话上限（与 <c>LocalSessionCacheLedger.MaxSessions</c> 同策：超限即清空，绝不无界增长）。</summary>
    public const int DefaultMaxSessions = 512;

    private readonly int _maxSessions;
    private readonly System.Collections.Concurrent.ConcurrentDictionary<string, SessionTurn> _bySession
        = new(StringComparer.Ordinal);
    private int _inFlight;
    private long _concurrentTurns;
    private long _maxInFlight;
    private long _unkeyedTurns;

    public LocalSessionTracker(int maxSessions = DefaultMaxSessions)
        => _maxSessions = maxSessions > 0 ? maxSessions : DefaultMaxSessions;

    /// <summary>某会话的上一轮读数（总长, 生成）。</summary>
    public readonly record struct SessionTurn(int TotalTokens, int GeneratedTokens);

    /// <summary>被使用计数: 当前记账的会话数。</summary>
    public int TrackedSessions => _bySession.Count;

    /// <summary>被使用计数: 观察到「同时有 ≥2 轮在飞」的轮次数（>0 ⇒ 该端口正在被并发使用）。</summary>
    public long ConcurrentTurns => Interlocked.Read(ref _concurrentTurns);

    /// <summary>被使用计数: 同时在飞轮数的历史峰值（1 = 纯串行；>1 才有 slot 争用这一 regime）。</summary>
    public long MaxConcurrentTurns => Interlocked.Read(ref _maxInFlight);

    /// <summary>被使用计数: 未带 sessionKey 的轮次数（这些轮只能按实例级兜底，分桶对它们无效）。</summary>
    public long UnkeyedTurns => Interlocked.Read(ref _unkeyedTurns);

    /// <summary>当前在飞轮数（诊断用；归零说明没有泄漏的租约）。</summary>
    public int TurnsInFlight => Volatile.Read(ref _inFlight);

    /// <summary>
    /// 进入一轮（并发可见性 + 租约）。必须 <c>using</c> 使用，异常路径也要退出计数。
    /// </summary>
    public IDisposable EnterTurn(string? sessionKey)
    {
        if (string.IsNullOrEmpty(sessionKey))
            Interlocked.Increment(ref _unkeyedTurns);

        var now = Interlocked.Increment(ref _inFlight);
        UpdateMax(now);
        if (now > 1)
            Interlocked.Increment(ref _concurrentTurns);

        return new TurnLease(this);
    }

    /// <summary>
    /// 本会话的可复用上限 = 上一轮总长 + 上一轮生成；无记录 ⇒ 0（首轮）。
    /// <paramref name="sessionKey"/> 为空 ⇒ 退回实例级 <paramref name="fallbackTotal"/>/<paramref name="fallbackGenerated"/>。
    /// </summary>
    public int CeilingFor(string? sessionKey, int fallbackTotal, int fallbackGenerated)
    {
        if (!string.IsNullOrEmpty(sessionKey))
        {
            return _bySession.TryGetValue(sessionKey, out var t)
                ? t.TotalTokens + Math.Max(0, t.GeneratedTokens)
                : 0;
        }

        return fallbackTotal >= 0 ? fallbackTotal + Math.Max(0, fallbackGenerated) : 0;
    }

    /// <summary>记录一轮完成后的读数。无 <c>sessionKey</c> ⇒ 不记（调用方应改用实例级兜底）。</summary>
    public void Record(string? sessionKey, int totalTokens, int generatedTokens)
    {
        if (string.IsNullOrEmpty(sessionKey))
            return;

        if (_bySession.Count >= _maxSessions && !_bySession.ContainsKey(sessionKey))
            _bySession.Clear();   // 有界策略：与台账同策，宁可丢旧会话也不无界增长

        _bySession[sessionKey] = new SessionTurn(totalTokens, Math.Max(0, generatedTokens));
    }

    /// <summary>清空（诊断/测试用；不影响计数）。</summary>
    public void Clear() => _bySession.Clear();

    private void UpdateMax(int candidate)
    {
        while (true)
        {
            var cur = Interlocked.Read(ref _maxInFlight);
            if (candidate <= cur || Interlocked.CompareExchange(ref _maxInFlight, candidate, cur) == cur)
                return;
        }
    }

    private void ExitTurn() => Interlocked.Decrement(ref _inFlight);

    private sealed class TurnLease(LocalSessionTracker owner) : IDisposable
    {
        private LocalSessionTracker? _owner = owner;
        public void Dispose()
        {
            var o = Interlocked.Exchange(ref _owner, null);
            o?.ExitTurn();
        }
    }
}
