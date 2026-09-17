namespace agent.exploration;


/// <summary>
/// R449: think-memory 计数器 — 反「空心读数」闸。任何「开关有效果」的结论必须先满足
/// <c>Recalls &gt; 0</c> (尝试过召回) 或 <c>Writes &gt; 0</c>, 否则该臂记 n/a 而不是 0
/// (R380 铁律: 「没测到」≠「测过通过/无效果」)。
/// </summary>
public static class ThinkMemoryStats
{
    private static int _writes, _writesSuppressed, _negativeWrites, _unbackedWrites;
    private static int _recalls, _recallsSuppressed, _recallHits, _dimMismatch;
    private static int _hits, _refHits, _loaded;

    public static void RecordWrite(bool isNegative, int refCount)
    {
        Interlocked.Increment(ref _writes);
        if (isNegative) Interlocked.Increment(ref _negativeWrites);
        if (refCount <= 0) Interlocked.Increment(ref _unbackedWrites);
    }

    public static void RecordWriteSuppressed() => Interlocked.Increment(ref _writesSuppressed);
    public static void RecordRecallAttempt() => Interlocked.Increment(ref _recalls);
    public static void RecordRecallSuppressed() => Interlocked.Increment(ref _recallsSuppressed);
    public static void RecordRecallHits(int n) { if (n > 0) Interlocked.Add(ref _recallHits, n); }
    public static void RecordDimMismatch() => Interlocked.Increment(ref _dimMismatch);
    public static void RecordHit() => Interlocked.Increment(ref _hits);
    public static void RecordRefHit() => Interlocked.Increment(ref _refHits);
    public static void RecordLoaded(int n) => Interlocked.Add(ref _loaded, n);

    public static (int Writes, int WritesSuppressed, int NegativeWrites, int UnbackedWrites,
                   int Recalls, int RecallsSuppressed, int RecallHits, int DimMismatch,
                   int Hits, int RefHits, int Loaded) Snapshot()
        => (Volatile.Read(ref _writes), Volatile.Read(ref _writesSuppressed), Volatile.Read(ref _negativeWrites),
            Volatile.Read(ref _unbackedWrites), Volatile.Read(ref _recalls), Volatile.Read(ref _recallsSuppressed),
            Volatile.Read(ref _recallHits), Volatile.Read(ref _dimMismatch), Volatile.Read(ref _hits),
            Volatile.Read(ref _refHits), Volatile.Read(ref _loaded));

    /// <summary>测试/测量用 (生产不调用)。</summary>
    public static void Reset()
    {
        Interlocked.Exchange(ref _writes, 0); Interlocked.Exchange(ref _writesSuppressed, 0);
        Interlocked.Exchange(ref _negativeWrites, 0); Interlocked.Exchange(ref _unbackedWrites, 0);
        Interlocked.Exchange(ref _recalls, 0); Interlocked.Exchange(ref _recallsSuppressed, 0);
        Interlocked.Exchange(ref _recallHits, 0); Interlocked.Exchange(ref _dimMismatch, 0);
        Interlocked.Exchange(ref _hits, 0); Interlocked.Exchange(ref _refHits, 0);
        Interlocked.Exchange(ref _loaded, 0);
    }
}
