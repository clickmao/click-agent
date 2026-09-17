using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>节点运行状态</summary>
public enum PlanNodeState
{
    Pending,

    /// <summary>
    /// 等待其它节点产出 (v0.22.0 exp9 D7 运行时依赖): A 跑到中途发现要用 B 的产出, 而 B 尚未产出
    /// (在跑 / 在等用户澄清) ⇒ A 进本状态, **不消费输入、不伪造数据、不静默降级**。
    /// 生产节点落终态后由调度器唤醒 (详情见 TaskPlanRun.Waits)。
    /// </summary>
    Waiting,

    AwaitingClarification,
    AwaitingApproval,
    Running,
    Completed,
    Failed,
    Skipped,
}
