using Xunit;
using agent.intent;
using agent.registry;

namespace agent.tests;

/// <summary>
/// v0.23.0 exp13 · §3 WaitUs 墙钟锚点单测。
/// 目的: 跨进程等待**可对账**（R384 遗留: 单调时钟零点随进程变化, `wait_ms=9` 只能自证, 无法与外部时间线对账）。
/// 判据(逐条可证伪, 含负向控制):
///  1) 锚点与时长**同一写点**落地 (End() 同时落 EndedUs + EndedWallUtcMs);
///  2) 本记录内不倒流: EndWall >= StartWall;
///  3) 跨记录时间线不倒流: 前者起点 <= 后者终点;
///  4) **负向控制**: 人为倒流的锚点必须被判为不可对账 —— 否则判据形同虚设。
/// </summary>
public sealed class WaitWallClockTests
{
    private static NodeWaitRecord NewWaiting(long startUs = 1_000_000L) => new("a", "b", "queued", startUs)
    {
        StartedWallUtcMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
    };

    [Fact]
    public void End_StampsBothClocks_AndKeepsDurationFromMonotonicClock()
    {
        var w = NewWaiting(1_000_000L);
        Assert.Null(w.EndedUs);
        Assert.Null(w.EndedWallUtcMs);
        Assert.Null(w.WaitUs);

        w.End(1_009_000L);   // 9ms

        Assert.Equal(1_009_000L, w.EndedUs);
        Assert.Equal(9_000L, w.WaitUs);                     // 时长只认单调时钟
        Assert.NotNull(w.EndedWallUtcMs);                   // 锚点同写点落地
        Assert.True(w.WallClockReconciled());
    }

    [Fact]
    public void Reconciled_IsFalse_WhenAnchorMissing_OldCheckpoint()
    {
        var old = new NodeWaitRecord("a", "b", "queued", 1L) { EndedUs = 2L };  // 老格式: 无锚点
        Assert.False(old.WallClockReconciled());
        Assert.Null(old.StartedWallUtcMs);
        Assert.Null(old.EndedWallUtcMs);
    }

    [Fact] // 负向控制: 倒流必须被抓到
    public void Reconciled_IsFalse_OnReversedWallClock()
    {
        var w = NewWaiting();
        w.End(2L);
        w.StartedWallUtcMs = 5_000L;   // 人为让起点晚于终点 (时钟回拨/锚点写错)
        w.EndedWallUtcMs = 4_000L;
        Assert.False(w.WallClockReconciled());
    }

    [Fact]
    public void Ordered_AcrossRecords_HoldsForForwardTimeline()
    {
        var earlier = NewWaiting();
        earlier.End(2_000_000L);
        var later = new NodeWaitRecord("c", "d", "user", 3_000_000L)
        {
            StartedWallUtcMs = earlier.EndedWallUtcMs,
        };
        later.End(3_500_000L);

        Assert.True(NodeWaitRecord.WallClockOrdered(earlier, later));
    }

    [Fact] // 负向控制: 跨记录倒流 (后一轮终点早于前一轮起点) 必须被判否
    public void Ordered_IsFalse_OnBackwardsTimeline()
    {
        var earlier = NewWaiting();
        earlier.End(2_000_000L);
        earlier.StartedWallUtcMs = 10_000L;
        var later = new NodeWaitRecord("c", "d", "user", 3_000_000L) { StartedWallUtcMs = 20_000L };
        later.End(3_500_000L);
        later.EndedWallUtcMs = 9_000L;   // 后一轮终点早于前一轮起点

        Assert.False(NodeWaitRecord.WallClockOrdered(earlier, later));
    }

    [Fact]
    public void Ordered_IsFalse_WhenLaterHasNoAnchor()
    {
        var earlier = NewWaiting();
        earlier.End(2L);
        var later = new NodeWaitRecord("c", "d", "user", 3L) { EndedUs = 4L };   // 无锚点
        Assert.False(NodeWaitRecord.WallClockOrdered(earlier, later));
    }
}
