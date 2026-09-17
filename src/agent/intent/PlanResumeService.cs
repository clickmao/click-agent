using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using agent.recovery;

namespace agent.intent;

/// <summary>
/// 计划续跑服务 (v0.22.0 exp9 D7b) —— 补上"装载入口 + 续跑消费方"这块结构缺口。
///
/// 背景: R383 的 D7a 能让节点 A 在运行中途停下来等 B 的产出; 但若 B 在等用户回答,
/// 计划就停在 PausedForDependency —— 下一轮用户答复**不会有任何消费方** (旧实现只会把答复当成一个全新任务重拆)。
///
/// 本服务的三件事 (全部确定性, 零 LLM):
///   ① Capture  — 暂停时把 蓝图/运行态/真产出 写进检查点 (老检查点没有蓝图 → 不可续跑);
///   ② TryLoad  — 下一轮把检查点**装载**回候选 (缺任何一件 → 如实拒绝, 不猜测重建);
///   ③ ApplyReply — 把用户答复落到确定的参数槽 (条目无参数名/答复不在选项内 → 拒绝), 清澄清, 置 Pending。
///
/// 拒绝原因一律以可读事实返回, 由调用方原样呈现 —— 不许降级成"重拆一遍"冒充续跑。
/// </summary>
public static class PlanResumeService
{
    public const string RefuseNoCheckpoint = "上一轮没有检查点 (没有未完成的计划)";
    public const string RefuseNoPayload = "检查点缺蓝图/运行态快照 (老格式) — 重建等于重拆任务, 不是续跑, 拒绝";
    public const string RefuseRunTerminal = "上一轮计划已到终态 (Finished/Cancelled) — 无需续跑";
    public const string RefuseNotAwaitingUser = "上一轮没有节点在等用户回复 — 没有答复可落地";
    public const string RefuseNoSlot = "澄清条目没有参数名, 答复落不到确定位置 — 拒绝 (不猜)";
    public const string RefuseMultiItem = "该节点有多条澄清要一次答复 — 本轮只支持单条目答复协议, 拒绝 (不猜位置)";
    public const string RefuseChoiceMismatch = "答复不在该条目的可选范围内";
    public const string RefuseMissingOutputs = "等待节点要吃的产出不在检查点快照里 — 续跑只能伪造或重跑生产者, 两者都不接受";

    /// <summary>R458 禁上前台的内部术语 (机检用: 人话承接句一律不得包含这些词)。</summary>
    public static readonly string[] InternalJargon = ["可选范围", "检查点", "作废", "槽位"];

    /// <summary>
    /// R458/R460 人性化承接句: 把"答复落不到槽位 ⇒ 检查点作废"的内部判定变成一句人话 —— 像人一样先承接、
    /// 只说两个事实 (上一轮在等你回答什么 / 这轮内容对不上), 不出现内部术语, 也不复述内部示例枚举。
    /// R460 精炼令: 从 78 字符压到 ≤ <see cref="MaxNoticeChars"/> (用户令「r458回复要精炼」)。
    /// why (内部理由) 不呈现给用户 —— 调用方仍把它送遥测, 事实不丢。
    /// </summary>
    public static string HumanizeVoidNotice(string? pendingQuestion, string? why)
    {
        _ = why; // 内部理由只进遥测 (调用方 Emit), 不上前台
        var q = CompactQuestion(pendingQuestion, 16);
        return q.Length > 0
            ? "(先说明: 上一轮问过「" + q + "」还没答, 这轮按你这次的意图办。)"
            : "(先说明: 上一轮的问题还没答, 这轮按你这次的意图办。)";
    }

    /// <summary>R460: 人话承接句的硬上限 (机检: HumanizeVoidNotice ≤ 此值)。</summary>
    public const int MaxNoticeChars = 48;

    /// <summary>
    /// 压缩待答问题成"人话主语": 优先取问句里引用的**用户原话** (「…」), 否则取首句;
    /// 再去括号/方括号补充说明 (示例枚举、参数说明都不上台面), 最后截断。
    /// 只用真实文本, 不重写语义。
    /// </summary>
    public static string CompactQuestion(string? q, int max = 40)
    {
        if (string.IsNullOrWhiteSpace(q)) return string.Empty;
        var t = q.Trim();
        var open = t.IndexOf('「');
        if (open >= 0)
        {
            var close = t.IndexOf('」', open + 1);
            if (close > open + 1) t = t.Substring(open + 1, close - open - 1);
        }
        else
        {
            var cut = t.IndexOfAny(['。', '?', '？', '!', '！', '\n']);
            if (cut > 0) t = t[..(cut + 1)];
        }
        t = StripEnclosed(t, '(', ')', null);
        t = StripEnclosed(t, '（', '）', null);
        t = StripEnclosed(t, '[', ']', null);
        t = t.Trim();
        if (t.Length > max) t = t[..max];
        return t.TrimEnd(' ', ',', '，', ';', '；', ':', '：', '—', '-');
    }

    private static string StripEnclosed(string s, char open, char close, string? mustContain)
    {
        var i = s.IndexOf(open);
        while (i >= 0)
        {
            var j = s.IndexOf(close, i + 1);
            if (j < 0) break;
            var inner = s.Substring(i + 1, j - i - 1);
            if (mustContain is null || inner.Contains(mustContain, StringComparison.Ordinal))
            {
                s = s.Remove(i, j - i + 1);
                i = s.IndexOf(open);
            }
            else
            {
                i = s.IndexOf(open, j + 1);
            }
        }
        return s;
    }

    /// <summary>
    /// ① 捕获: 计划停下来 (等用户 / 等产出) 时把续跑三件套落盘。
    /// 返回 false = 没写 (store 未注入 / 会话 Id 空 / 计划已正常跑完 —— 正常完成不需要续跑入口)。
    /// </summary>
    public static bool Capture(
        CheckpointStore? store, string sessionId, TaskPlan plan, TaskPlanRun run,
        IReadOnlyDictionary<string, string?>? outputs, string? sourceText)
    {
        if (store is null || string.IsNullOrEmpty(sessionId))
            return false;

        // 只捕获"有节点在等用户**文字答复**"的暂停态: 等审批(AwaitingApproval)有自己的答复协议,
        // 捕获它= 把它拦进续跑入口(reply 落不到澄清参数槽) ⇒ 会吞掉审批消息 (不许)。
        var awaitingId = AwaitingNodeIdOf(run, plan);
        if (!IsClarificationAwaiting(run, plan, awaitingId))
            return false;

        var snap = new Dictionary<string, string>(StringComparer.Ordinal);
        if (outputs is not null)
            foreach (var kv in outputs)
                if (!string.IsNullOrEmpty(kv.Value))
                    snap[kv.Key] = kv.Value!;

        store.Save(new ExecutionCheckpoint
        {
            SessionId = sessionId,
            PlanId = run.PlanId,
            RunId = run.RunId,
            NodeStates = run.NodeStates.ToDictionary(kv => kv.Key, kv => kv.Value.ToString()),
            PauseReason = run.PauseReason,
            PlanJson = JsonSerializer.Serialize(plan, TaskPlanJsonContext.Default.TaskPlan),
            RunJson = JsonSerializer.Serialize(run, TaskPlanJsonContext.Default.TaskPlanRun),
            NodeOutputs = snap,
            SourceText = sourceText,
            AwaitingNodeId = awaitingId,
            PendingQuestion = awaitingId is null
                ? null
                : plan.Nodes.FirstOrDefault(n => n.Id == awaitingId)?
                      .Clarifications.FirstOrDefault()?.Question,
        });
        return true;
    }

    /// <summary>
    /// ② 装载: 读检查点 → 重建 (计划, 运行态)。任何一件缺失都如实返回原因, 绝不"尽力重建"。
    /// </summary>
    public static bool TryLoad(
        CheckpointStore? store, string sessionId, out PlanResumeCandidate? candidate, out string reason)
    {
        candidate = null;
        reason = RefuseNoCheckpoint;
        if (store is null || string.IsNullOrEmpty(sessionId))
            return false;

        var cp = store.Load(sessionId);
        if (cp is null)
            return false;

        if (string.IsNullOrEmpty(cp.PlanJson) || string.IsNullOrEmpty(cp.RunJson))
        {
            reason = RefuseNoPayload;
            return false;
        }

        TaskPlan? plan;
        TaskPlanRun? run;
        try
        {
            plan = JsonSerializer.Deserialize(cp.PlanJson, TaskPlanJsonContext.Default.TaskPlan);
            run = JsonSerializer.Deserialize(cp.RunJson, TaskPlanJsonContext.Default.TaskPlanRun);
        }
        catch (JsonException)
        {
            reason = RefuseNoPayload; // 损坏快照 = 没有快照, 不猜
            return false;
        }

        if (plan is null || run is null)
        {
            reason = RefuseNoPayload;
            return false;
        }

        // 取消 = 用户明确放弃 ⇒ 不自动续跑; Finished 则要看下面"有没有节点在等用户"再定 (计划本轮跑完
        // 但某节点卡在等澄清时, State 也会是 Finished —— 那不是"任务完成", 是"等你回答")。
        if (run.State is TaskPlanRunState.Cancelled)
        {
            reason = RefuseRunTerminal;
            return false;
        }

        var awaitingId = AwaitingNodeIdOf(run, plan) ?? cp.AwaitingNodeId;
        var awaitingValid = !string.IsNullOrEmpty(awaitingId)
                            && plan.Nodes.FirstOrDefault(n => n.Id == awaitingId) is { Clarifications.Count: > 0 }
                            && run.NodeStates.TryGetValue(awaitingId!, out var awaitingState)
                            && awaitingState == PlanNodeState.AwaitingClarification;
        if (!awaitingValid)
        {
            reason = run.State is TaskPlanRunState.Finished ? RefuseRunTerminal : RefuseNotAwaitingUser;
            return false;
        }

        // 防伪造 (D7b 硬纪律②): 等待节点要吃的产出必须在快照里 —— 缺了就只能"空着喂"(伪造)或
        // 重跑生产者(重复副作用), 两者都不可接受 ⇒ 装载入口直接拒绝, 由调用方如实告知。
        foreach (var kv in run.NodeStates.Where(x => x.Value == PlanNodeState.Waiting))
        {
            var waitingNode = plan.Nodes.FirstOrDefault(n => n.Id == kv.Key);
            if (waitingNode is null)
                continue;
            var producer = RuntimeDependencyScanner.FindProducer(waitingNode, plan.Nodes);
            if (producer is null)
                continue;
            if (run.NodeStates.TryGetValue(producer, out var ps) && ps == PlanNodeState.Completed
                && !cp.NodeOutputs.ContainsKey(producer))
            {
                reason = $"{RefuseMissingOutputs} (节点 {kv.Key} ← {producer})";
                return false;
            }
        }

        candidate = new PlanResumeCandidate
        {
            Plan = plan,
            Run = run,
            NodeOutputs = cp.NodeOutputs,
            SourceText = cp.SourceText ?? plan.SourceText,
            AwaitingNodeId = awaitingId!,
            AwaitingParameterNames = plan.Nodes.First(n => n.Id == awaitingId)
                .Clarifications.Select(c => c.ParameterName).ToList(),
            PendingQuestion = cp.PendingQuestion,
        };
        reason = string.Empty;
        return true;
    }

    /// <summary>
    /// ③ 落地答复: 把用户这一轮的消息写进等用户节点的参数槽, 清澄清, 节点转 Pending (等待节点会在同一轮被唤醒)。
    /// 拒绝条件: 条目无参数名 / 多条目 (无位置协议) / 答复不在选项内。
    /// </summary>
    public static bool ApplyReply(PlanResumeCandidate candidate, string reply, out string reason)
    {
        reason = string.Empty;
        var text = (reply ?? string.Empty).Trim();
        if (text.Length == 0)
        {
            reason = "答复为空 — 不落地 (不拿空串占住参数槽)";
            return false;
        }

        var node = candidate.AwaitingNode;
        var items = node.Clarifications.ToList();
        if (items.Count == 0)
        {
            reason = RefuseNotAwaitingUser;
            return false;
        }

        // 多条目 = 需要位置协议 (逐项答复): 本轮**不猜**位置, 如实拒绝并把协议留作下轮候选。
        if (items.Count > 1)
        {
            reason = RefuseMultiItem;
            return false;
        }

        var item = items[0];
        if (string.IsNullOrWhiteSpace(item.ParameterName))
        {
            reason = RefuseNoSlot;
            return false;
        }

        if (item.Choices.Count > 0
            && !item.Choices.Any(x => string.Equals(x, text, StringComparison.OrdinalIgnoreCase)))
        {
            reason = $"{RefuseChoiceMismatch} [{string.Join('/', item.Choices)}]";
            return false;
        }

        var slot = node.Parameters.FirstOrDefault(p =>
            string.Equals(p.Name, item.ParameterName, StringComparison.Ordinal));
        if (slot is null)
        {
            slot = new TaskParameter
            {
                Name = item.ParameterName,
                DisplayName = item.ParameterName,
                IsRequired = true,
            };
            node.Parameters.Add(slot);
        }
        slot.Value = text;

        // 澄清结清: 清条目 + 打标记 —— 不打卡片, 证据门槛会按同一低置信度把刚答过的问题再问一遍。
        node.Clarifications.Clear();
        node.ClarificationsSettled = true;

        candidate.Run.NodeStates[node.Id] = PlanNodeState.Pending;
        candidate.Run.State = TaskPlanRunState.Running;
        candidate.Run.PauseReason = null;
        return true;
    }

    /// <summary>
    /// 该节点是不是"在等用户**文字答复**"(= 续跑入口能落地的形态)。
    /// 等审批(`AwaitingApproval`)不算: 它有独立的答复协议, 被续跑入口拦下会**吞掉审批消息**。
    /// </summary>
    private static bool IsClarificationAwaiting(TaskPlanRun run, TaskPlan plan, string? nodeId)
        => !string.IsNullOrEmpty(nodeId)
           && run.NodeStates.TryGetValue(nodeId!, out var st)
           && st == PlanNodeState.AwaitingClarification
           && plan.Nodes.FirstOrDefault(n => n.Id == nodeId) is { Clarifications.Count: > 0 };

    /// <summary>
    /// 卡在等用户的节点: 优先按 Clarifications 判定 (有具体问题才有"答复"可言),
    /// 否则退回状态名判定 (ClarificationItem 可能已被其他路径清掉)。
    /// </summary>
    public static string? AwaitingNodeIdOf(TaskPlanRun run, TaskPlan plan)
    {
        foreach (var node in plan.Nodes)
        {
            if (!run.NodeStates.TryGetValue(node.Id, out var st))
                continue;
            if (st is PlanNodeState.AwaitingClarification or PlanNodeState.AwaitingApproval
                && node.Clarifications.Count > 0)
                return node.Id;
        }

        foreach (var kv in run.NodeStates)
            if (kv.Value is PlanNodeState.AwaitingClarification or PlanNodeState.AwaitingApproval)
                return kv.Key;

        return null;
    }
}
