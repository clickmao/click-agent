using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using agent.recovery;

namespace agent.intent;


/// <summary>
/// 续跑候选 (v0.22.0 exp9 D7b): 从检查点**重建**出来的"上一轮没跑完的计划"。
/// 三件套齐备才算候选: 蓝图 (跑什么/依赖/位置) + 运行态 (跑到哪/谁在等谁) + 已完成节点真产出。
/// </summary>
public sealed class PlanResumeCandidate
{
    public required TaskPlan Plan { get; init; }

    public required TaskPlanRun Run { get; init; }

    /// <summary>已完成节点的真产出 (NodeId → 输出) —— 唤醒等待节点靠它, 不靠重跑/不靠编</summary>
    public required Dictionary<string, string> NodeOutputs { get; init; }

    /// <summary>本轮原始请求 (无依赖节点的输入来源)</summary>
    public string? SourceText { get; init; }

    /// <summary>卡在等用户回复的节点 Id</summary>
    public required string AwaitingNodeId { get; init; }

    /// <summary>给用户看的问题 (与节点 Clarifications 同源)</summary>
    public string? PendingQuestion { get; init; }

    public PlanNode AwaitingNode =>
        Plan.Nodes.FirstOrDefault(n => n.Id == AwaitingNodeId)
        ?? throw new InvalidOperationException($"检查点指向的节点 {AwaitingNodeId} 不在蓝图里 — 候选不合法");

    /// <summary>
    /// 等用户的节点挂在哪些参数槽上 (前端/日志可显示"答复将落到哪")。
    /// 装载时**快照**一次: 答复落地后 Clarifications 会被清空, 现算就会变成空 —— 那会让
    /// "答复落到了哪个槽"这条事实在事后不可对账。
    /// </summary>
    public required IReadOnlyList<string> AwaitingParameterNames { get; init; }
}
