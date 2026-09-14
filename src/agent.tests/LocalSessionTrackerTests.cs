using agent.llamacpp;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R412 J1: 本地生成的**会话级账本**（<see cref="LocalSessionTracker"/>）—— 纯逻辑，不需要 llama-server。
///
/// 背景（R412 代码事实）: 长驻端口按设计是进程内单例（一个 server 服务所有会话），
/// 而 <c>LlamaCppTextGenerator.LastPromptTokens/LastGeneratedTokens</c> 是**实例级唯一**的
/// ⇒ 多会话交替/并发时，A 会话下一轮读到的「上一轮」可能是 B 会话的 ⇒ 交给 K2b 台账的
/// <c>carryOverCeiling</c>（分母）被污染，判红/判绿都可能失真且外部看不出。
///
/// 判据（R412 计划 §1.3 ⇔ 本文件）:
///   J1a 分桶: 交互写入两个会话后，各自 ceiling 只由自己的上一轮决定（反例: 实例级会给别人的值）
///   J1b 首轮: 无记录 ⇒ 0（不是 -1、不是别人的）
///   J1c 无键兜底: sessionKey 为空 ⇒ 退回实例级（无会话形态零回归）；且无键的 Record 不得建桶
///   J1d 并发计数: 同时 ≥2 轮在飞 ⇒ MaxConcurrentTurns ≥2、ConcurrentTurns 递增；租约释放后归零
///   J1e 负控: 纯串行 ⇒ MaxConcurrentTurns == 1 且 ConcurrentTurns == 0（不得误报争用）
///   J1f 有界: 超过 maxSessions ⇒ 不无界增长（与台账同策: 清空）
///   J1g 夹紧: 生成数为负（脏输入）⇒ 不得把 ceiling 拉低（夹到 0）
///   J1h 接线: 端口把账本暴露给调用方（<c>LlamaCppTextGenerator.Sessions</c>），零 I/O 可构造
/// </summary>
public sealed class LocalSessionTrackerTests
{
    [Fact]
    public void J1a_TwoSessions_EachKeepsOwnCeiling()
    {
        var t = new LocalSessionTracker();
        t.Record("s1", 500, 10);   // 会话 1 上一轮: 总长 500 / 生成 10
        t.Record("s2", 400, 8);    // 会话 2 覆盖实例级视角

        // 会话 1 的 ceiling 必须是 510；实例级实现会给 408（= 408 = 400+8，别人的上一轮）
        Assert.Equal(510, t.CeilingFor("s1", 400, 8));
        Assert.Equal(408, t.CeilingFor("s2", 500, 10));
        Assert.Equal(2, t.TrackedSessions);
        Assert.NotEqual(t.CeilingFor("s1", 400, 8), 400 + Math.Max(0, 8));
    }

    [Fact]
    public void J1b_FirstTurn_IsZero()
        => Assert.Equal(0, new LocalSessionTracker().CeilingFor("fresh", 999, 999));

    [Fact]
    public void J1c_Unkeyed_FallsBackToInstance_AndDoesNotTrack()
    {
        var t = new LocalSessionTracker();
        Assert.Equal(705, t.CeilingFor(null, 700, 5));
        Assert.Equal(0, t.CeilingFor(null, -1, 5));      // 尚未生成 ⇒ 0

        t.Record(null, 700, 5);                          // 无键: 不得建桶
        using (t.EnterTurn(null)) { }                     // 无键轮次计数（Record 不是轮次）
        Assert.Equal(0, t.TrackedSessions);
        Assert.Equal(1, t.UnkeyedTurns);
    }

    [Fact]
    public void J1d_ConcurrentTurns_Counted_AndLeasesReleased()
    {
        var t = new LocalSessionTracker();
        var a = t.EnterTurn("s1");
        var b = t.EnterTurn("s2");                       // 同时在飞两轮
        Assert.Equal(2, t.TurnsInFlight);
        Assert.Equal(2, t.MaxConcurrentTurns);
        Assert.Equal(1, t.ConcurrentTurns);

        b.Dispose();
        a.Dispose();
        Assert.Equal(0, t.TurnsInFlight);                // 异常/正常路径都要归零
        Assert.Equal(2, t.MaxConcurrentTurns);           // 峰值保留（诊断用）
    }

    [Fact]
    public void J1e_NegativeControl_SerialOnly_NeverReportsContention()
    {
        var t = new LocalSessionTracker();
        for (var i = 0; i < 3; i++)
        {
            using (t.EnterTurn("s1"))
            {
                t.Record("s1", 100 + i, 2);
            }
        }

        Assert.Equal(1, t.MaxConcurrentTurns);
        Assert.Equal(0, t.ConcurrentTurns);
    }

    [Fact]
    public void J1f_Bounded_NoUnboundedGrowth()
    {
        var t = new LocalSessionTracker(maxSessions: 3);
        foreach (var s in new[] { "a", "b", "c", "d", "e" })
            t.Record(s, 10, 1);

        Assert.True(t.TrackedSessions <= 3, $"TrackedSessions={t.TrackedSessions} 超上限");
        Assert.Equal(11, t.CeilingFor("e", 0, 0));       // 最近写入的会话仍可用（10 + 1）
    }

    [Fact]
    public void J1g_NegativeGenerated_Clamped()
    {
        var t = new LocalSessionTracker();
        t.Record("s", 100, -7);
        Assert.Equal(100, t.CeilingFor("s", 0, 0));
    }

    [Fact]
    public void J1h_PortExposesTracker_ZeroIo()
    {
        var gen = new LlamaCppTextGenerator(new LlamaCppGeneratorOptions
        {
            ModelPath = "/nonexistent/model.gguf",
        });

        Assert.NotNull(gen.Sessions);
        Assert.Equal(0, gen.Sessions.TrackedSessions);
        Assert.Equal(0, gen.Sessions.MaxConcurrentTurns);
        Assert.False(gen.IsAvailable);                   // 纯配置判定: 文件不存在 ⇒ false（零 I/O 副作用）
    }
}
