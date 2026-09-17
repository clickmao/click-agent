using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>计划运行状态</summary>
public enum TaskPlanRunState
{
    /// <summary>执行中 (可被注入指令合并、被敏感节点暂停)</summary>
    Running,

    /// <summary>敏感节点等待用户审批 — 全计划暂停 (不可跳过继续)</summary>
    PausedForApproval,

    /// <summary>全部节点终态 (Completed/Failed/Skipped)</summary>
    Finished,

    /// <summary>
    /// 存在节点在等另一节点的产出, 而该生产节点在等用户 (澄清/审批) (v0.22.0 exp9 D7)。
    /// 本轮到此为止: 不许伪造数据硬跑 —— 用户回复后重跑 (跨轮唤醒 D7b 见计划 §12 边界)。
    /// </summary>
    PausedForDependency,

    /// <summary>用户或策略取消 (未完成节点标记 Skipped)</summary>
    Cancelled,
}
