using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Threading;

namespace agent.modelqueue;


/// <summary>
/// R498: 本地改写通道计数 (实例级, 挂在 <see cref="ModelQueueRouter"/> 上 —— 与 TurnGate/RelationJudge
/// 同形; **不用静态计数器**: 静态共享态正是本轮候选②要清掉的缺陷类)。
/// 口径: Succeeded + GuardRejected + Degraded* == Attempted 不是不变量 (尝试可能异常), 故逐项单列。
/// </summary>
public sealed class LocalParaphraseCounters
{
    private long _attempted;
    private long _succeeded;
    private long _guardRejected;
    private long _degradedNoSource;
    private long _degradedNoPort;
    private long _degradedEngine;
    private long _accountingViolations;
    private string? _lastRejectReason;

    /// <summary>尝试次数 (含失败)。</summary>
    public long Attempted => Interlocked.Read(ref _attempted);

    /// <summary>成功并由守卫放行的次数。</summary>
    public long Succeeded => Interlocked.Read(ref _succeeded);

    /// <summary>守卫拒收次数 (已归因到 <see cref="LastRejectReason"/>)。</summary>
    public long GuardRejected => Interlocked.Read(ref _guardRejected);

    /// <summary>无可改写来源 (无上一条实质答复) 而降级的次数。</summary>
    public long DegradedNoSource => Interlocked.Read(ref _degradedNoSource);

    /// <summary>无本地端口而降级的次数。</summary>
    public long DegradedNoPort => Interlocked.Read(ref _degradedNoPort);

    /// <summary>引擎失败/空回/记账违规而降级的次数。</summary>
    public long DegradedEngine => Interlocked.Read(ref _degradedEngine);

    /// <summary>记账恒等 (tokens_evaluated == prompt_n + cache_n) 违规次数 —— 违规结果**不采信** (R411)。</summary>
    public long AccountingViolations => Interlocked.Read(ref _accountingViolations);

    /// <summary>最近一次拒收/降级原因 (归因用)。</summary>
    public string? LastRejectReason => Volatile.Read(ref _lastRejectReason);

    /// <summary>记录一次尝试。</summary>
    public void RecordAttempt() => Interlocked.Increment(ref _attempted);

    /// <summary>记录成功。</summary>
    public void RecordSuccess() => Interlocked.Increment(ref _succeeded);

    /// <summary>记录守卫拒收 (附原因)。</summary>
    public void RecordGuardReject(string reason)
    {
        Interlocked.Increment(ref _guardRejected);
        Volatile.Write(ref _lastRejectReason, reason);
    }

    /// <summary>记录「无可改写来源」降级。</summary>
    public void RecordNoSource()
    {
        Interlocked.Increment(ref _degradedNoSource);
        Volatile.Write(ref _lastRejectReason, "no_source");
    }

    /// <summary>记录「无本地端口」降级。</summary>
    public void RecordNoPort()
    {
        Interlocked.Increment(ref _degradedNoPort);
        Volatile.Write(ref _lastRejectReason, "no_local_port");
    }

    /// <summary>记录引擎面降级 (失败/空回/记账违规)。</summary>
    public void RecordEngineDegrade(string reason)
    {
        Interlocked.Increment(ref _degradedEngine);
        Volatile.Write(ref _lastRejectReason, reason);
    }

    /// <summary>记录记账违规。</summary>
    public void RecordAccountingViolation(string reason)
    {
        Interlocked.Increment(ref _accountingViolations);
        Volatile.Write(ref _lastRejectReason, reason);
    }
}
