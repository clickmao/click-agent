using agent.contextgradient;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.13.3 D4 — 熔断器单测 (标准工业模式 M4): 阈值触发/冷却/open 拒绝/半开放行/成功复位。
/// </summary>
public class CompressionBreakerTests
{
    [Fact]
    public void Closed_Allows_Attempts()
    {
        var b = new CompressionBreaker();
        Assert.True(b.AllowAttempt);
    }

    [Fact]
    public void Opens_After_Threshold_Failures()
    {
        var b = new CompressionBreaker(failureThreshold: 3, coolDownMs: 60_000);
        b.Record(false); b.Record(false); b.Record(false);
        Assert.False(b.AllowAttempt); // open: 冷却中拒绝
    }

    [Fact]
    public void Success_Before_Threshold_Resets()
    {
        var b = new CompressionBreaker(failureThreshold: 3, coolDownMs: 60_000);
        b.Record(false); b.Record(false);
        b.Record(true);
        b.Record(false); b.Record(false);
        Assert.True(b.AllowAttempt); // 未达 3 连败
    }

    [Fact]
    public void HalfOpen_Allows_Single_Trial_After_Cooldown()
    {
        var b = new CompressionBreaker(failureThreshold: 2, coolDownMs: 30);
        b.Record(false); b.Record(false);
        Assert.False(b.AllowAttempt); // open
        System.Threading.Thread.Sleep(40); // 冷却结束
        Assert.True(b.AllowAttempt);  // half-open 放行试探
        Assert.False(b.AllowAttempt); // 试探在途, 其余拒绝
    }

    [Fact]
    public void HalfOpen_Success_Closes_Breaker()
    {
        var b = new CompressionBreaker(failureThreshold: 2, coolDownMs: 30);
        b.Record(false); b.Record(false);
        System.Threading.Thread.Sleep(40);
        Assert.True(b.AllowAttempt); // 半开试探
        b.Record(true);
        Assert.True(b.AllowAttempt); // closed
    }

    [Fact]
    public void HalfOpen_Failure_Reopens()
    {
        var b = new CompressionBreaker(failureThreshold: 2, coolDownMs: 30);
        b.Record(false); b.Record(false);
        System.Threading.Thread.Sleep(40);
        Assert.True(b.AllowAttempt);  // 半开试探
        b.Record(false);              // 试探失败
        Assert.False(b.AllowAttempt); // 重新 open
    }
}
