using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;


/// <summary>R426: 关系判官本地化计数 (可观测 — <c>Local==0 ∧ Fallback&gt;0</c> ⇒ 本地未生效, 不靠猜)。</summary>
public sealed class RelationJudgeCounters
{
    private long _attempts;
    private long _local;
    private long _fallback;
    private long _accountingViolations;
    private long _cachePinned;

    public long Attempts => Interlocked.Read(ref _attempts);
    public long Local => Interlocked.Read(ref _local);
    public long Fallback => Interlocked.Read(ref _fallback);
    public long AccountingViolations => Interlocked.Read(ref _accountingViolations);

    /// <summary>R429: 判官显式关前缀缓存的次数。</summary>
    public long CachePinned => Interlocked.Read(ref _cachePinned);

    public string? LastSource { get; private set; }
    public string? LastLetter { get; private set; }

    public void RecordAttempt() => Interlocked.Increment(ref _attempts);

    /// <summary>R429: 判官请求已钉死缓存态 (显式关前缀缓存)。</summary>
    public void RecordCachePinned() => Interlocked.Increment(ref _cachePinned);

    public void RecordLocal(string letter)
    {
        Interlocked.Increment(ref _local);
        LastSource = "local";
        LastLetter = letter;
    }

    public void RecordFallback(string reason)
    {
        Interlocked.Increment(ref _fallback);
        LastSource = "remote_fallback:" + reason;
    }

    public void RecordAccountingViolation(string reason)
    {
        Interlocked.Increment(ref _accountingViolations);
        LastSource = "local:accounting_violation:" + reason + "→remote";
    }
}
