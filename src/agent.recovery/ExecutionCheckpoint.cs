using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.recovery;

/// <summary>
/// 任务步骤检查点 (v7.15 需求3: 工业级会话中断恢复):
/// 记录会话内最近一次计划执行到哪一步 — 意外中断/进程关闭后下次启动直接恢复进度。
/// 落盘 data/sessions/&lt;sessionId&gt;/checkpoint.json (原子写: tmp → File.Move)。
/// 序列化 source-gen (AOT 铁律: 无反射)。
/// </summary>
public sealed class ExecutionCheckpoint
{
    public string SessionId { get; set; } = string.Empty;

    /// <summary>计划 id (TaskPlan.PlanId)</summary>
    public string PlanId { get; set; } = string.Empty;

    /// <summary>RunId (TaskPlanRun.RunId)</summary>
    public string RunId { get; set; } = string.Empty;

    /// <summary>节点状态快照 (NodeId → 状态名)</summary>
    public Dictionary<string, string> NodeStates { get; set; } = new(StringComparer.Ordinal);

    /// <summary>最后完成的节点 id (恢复起点 = 其后第一个 Pending 节点)</summary>
    public string? LastCompletedNodeId { get; set; }

    /// <summary>检查点写入时刻 (UTC)</summary>
    public DateTime SavedAtUtc { get; set; } = DateTime.UtcNow;

    /// <summary>暂停原因 (中断时计划处于 PausedForApproval 则记录)</summary>
    public string? PauseReason { get; set; }

    /// <summary>
    /// 计划蓝图快照 JSON (v0.22.0 exp9 D7b — 缺了它就无法"重建 run": 光有节点状态名,
    /// 恢复后没有节点文本/依赖/执行位置, 只能重拆一遍 = 不是续跑)。
    /// 由 agent.intent 侧用 source-gen 上下文序列化; 本层(agent.recovery)不认识计划类型, 只当字符串存。
    /// null = 老检查点/无计划上下文 ⇒ 续跑必须**如实拒绝**, 不许猜测重建。
    /// </summary>
    public string? PlanJson { get; set; }

    /// <summary>运行实例快照 JSON (节点状态/等待台账/暂停原因; 同上, 字符串透传)</summary>
    public string? RunJson { get; set; }

    /// <summary>
    /// 已完成节点的**真实产出** (NodeId → 输出文本)。
    /// 续跑的关键: 唤醒等待节点要喂给它生产者的真产出 —— 没有这份快照就只能重跑生产者 (有副作用!)
    /// 或伪造数据。两者都不可接受 ⇒ 缺快照时续跑拒绝。
    /// </summary>
    public Dictionary<string, string> NodeOutputs { get; set; } = new(StringComparer.Ordinal);

    /// <summary>本轮用户原始请求 (续跑时无依赖节点的输入来源)</summary>
    public string? SourceText { get; set; }

    /// <summary>
    /// 卡在等用户回复的那个节点 (State=AwaitingClarification/Approval)。
    /// 非空 ⇒ 下一轮用户消息语义 = **答复它**, 不是新任务 (D7b 跨轮唤醒的入口判据)。
    /// </summary>
    public string? AwaitingNodeId { get; set; }

    /// <summary>等用户回复时给用户看的问题 (前端/CLI 提示用; 与节点 Clarifications 同源)</summary>
    public string? PendingQuestion { get; set; }
}
