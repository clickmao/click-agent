using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>
/// 单次运行时依赖等待 (v0.22.0 exp9 D7)。
/// Reason 语义 (确定性取值, 前端直接显示):
/// - `running`: 生产节点在本轮已启动, 尚未产出;
/// - `queued`: 生产节点尚未启动 (层级在后 / 并发额度未轮到);
/// - `user`: 生产节点在等用户澄清/审批 —— 它的产出依赖用户回复 (跨轮场景, 见 §12 D7b 边界)。
/// </summary>
public sealed record NodeWaitRecord(
    string NodeId,
    string ProducerId,
    string Reason,
    long StartedUs)
{
    /// <summary>唤醒时刻 (未唤醒为 null)</summary>
    public long? EndedUs { get; set; }

    /// <summary>
    /// 等待时长的墙钟锚点 (v0.23.0 exp13 · §3)。**只做锚点, 不做时长等价断言** ——
    /// 时长唯一事实源仍是 StartedUs/EndedUs 的进程内单调时钟; 墙钟仅用于跨进程/跨轮时间线对账,
    /// 因为单调时钟的零点随进程变化, 跨进程不可比。缺省 null = 无锚点 (老检查点/老测试构造)。
    /// </summary>
    public long? StartedWallUtcMs { get; set; }

    /// <inheritdoc cref="StartedWallUtcMs"/>
    public long? EndedWallUtcMs { get; set; }

    /// <summary>等待时长 (微秒; 未唤醒为 null)</summary>
    public long? WaitUs => EndedUs is null ? null : EndedUs - StartedUs;

    /// <summary>
    /// 唤醒 (v0.23.0 exp13 · §3): 单调时刻与墙钟锚点**同一写点**落地 ——
    /// 禁止两处各自取时钟 (那样锚点与时长会指向不同的瞬间, 对账就失去意义)。
    /// </summary>
    public void End(long endedUs)
    {
        EndedUs = endedUs;
        EndedWallUtcMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
    }

    /// <summary>§3-3 判据 1/3: 锚点齐全且本记录内不倒流。</summary>
    public bool WallClockReconciled()
        => StartedWallUtcMs is { } s && EndedWallUtcMs is { } e && e >= s;

    /// <summary>§3-3 判据 2: 跨进程/跨轮时间线不倒流 (前一轮的起点 ≤ 后一轮的终点)。</summary>
    public static bool WallClockOrdered(NodeWaitRecord earlier, NodeWaitRecord later)
        => earlier.StartedWallUtcMs is { } s && later.EndedWallUtcMs is { } e && e >= s;
}
