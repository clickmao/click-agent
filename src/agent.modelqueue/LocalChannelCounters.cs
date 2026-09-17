using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;


/// <summary>
/// 本地通道计数 (可观测/对账; 全部 Interlocked)。纪律: 未尝试 ⇒ <see cref="Attempted"/>==0,
/// 「没测到」不得当成「通过」——外部判红判绿都要看这四个数。
/// </summary>
public sealed class LocalChannelCounters
{
    /// <summary>真实发起过的本地生成次数 (端口被判据放行后才计)。</summary>
    public long Attempted;

    /// <summary>本地生成成功并直接作为本轮结果返回的次数。</summary>
    public long Succeeded;

    /// <summary>本地发起但失败/记账违规 ⇒ 降级远端的次数 (降级必须可见)。</summary>
    public long Degraded;

    /// <summary>判据拒绝次数 (未发起; 原因见 <see cref="LastRejectReason"/>)。</summary>
    public long Rejected;

    /// <summary>记账恒等式违规次数 (tokens_evaluated != prompt_n + cache_n)。</summary>
    public long AccountingViolations;

    public string? LastRejectReason;
    public string? LastDegradeReason;

    public void RecordAttempt() => Interlocked.Increment(ref Attempted);
    public void RecordSuccess() => Interlocked.Increment(ref Succeeded);
    public void RecordDegrade(string reason)
    {
        Interlocked.Increment(ref Degraded);
        LastDegradeReason = reason;
    }
    public void RecordReject(string reason)
    {
        Interlocked.Increment(ref Rejected);
        LastRejectReason = reason;
    }
    public void RecordAccountingViolation(string reason)
    {
        Interlocked.Increment(ref AccountingViolations);
        LastDegradeReason = reason;
    }

    public long Total => Interlocked.Read(ref Attempted) + Interlocked.Read(ref Rejected);
}
