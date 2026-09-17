using Microsoft.Extensions.Logging;
using agent.core;
using agent.workspace;
using agent.codegen;
using agent.recovery;
using agent.vectormemory;
using agent.memory;
using agent.templates;
using agent.search;
using agent.session;
using agent.context;
using agent.rag;
using agent.tendency;
using agent.tokencompression;
using agent.registry;

using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text;

using agent.intent;

namespace agent;

public partial class IndustrialAgentV2 : AgentBase
{

    /// <summary>R457: 落不到槽位 ⇒ 作废检查点并同轮转正常任务路径 (env AGENTFRAMEWORK_PLAN_RESUME_FALLTHROUGH, 默认 on)。</summary>
    internal static bool PlanResumeFallthrough()
    {
        var v = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_PLAN_RESUME_FALLTHROUGH");
        if (string.IsNullOrEmpty(v)) return true;
        return v.Equals("on", StringComparison.OrdinalIgnoreCase)
               || v.Equals("1", StringComparison.Ordinal)
               || v.Equals("true", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// D7b 跨轮唤醒 (真续跑): 检查点 → 装载 → 答复落到确定参数槽 → 从**上轮运行态**继续跑。
    /// 三条硬纪律:
    ///   ① 不重拆: 走出这条路就**不再**把这一轮消息当新任务 (用户答的就是上一轮那个问题);
    ///   ② 不伪造: 唤醒等待节点喂的是检查点里的**真产出** (缺产出快照 = 装载入口直接拒绝);
    ///   ③ 不吞: 答复落不到确定位置 (无参数名 / 多条目 / 不在选项内) → 如实告诉用户并作废该检查点,
    ///      既不静默丢弃, 也不把答复硬塞进一个猜出来的槽。
    /// </summary>
    private async Task<bool> TryResumePausedPlanAsync(Message message, AgentResponse response, CancellationToken ct)
    {
        if (string.IsNullOrEmpty(message.SessionId))
            return false;

        var store = _planCheckpoints ??= new agent.recovery.CheckpointStore(_dataStoragePath);
        if (!agent.intent.PlanResumeService.TryLoad(store, message.SessionId, out var cand, out var why) || cand is null)
        {
            // 没有未完成计划 = 常态 (普通消息都走这里): 只在"有检查点却装不回来"时留痕, 不刷噪声
            if (why != agent.intent.PlanResumeService.RefuseNoCheckpoint)
                agent.config.AgentTelemetry.Emit("plan_resume", "IndustrialAgentV2",
                    ("resumed", false), ("reason", why));
            return false;
        }

        if (!agent.intent.PlanResumeService.ApplyReply(cand, message.Content, out var applyWhy))
        {
            store.Clear(message.SessionId);
            // R458 人性化: 内部判定 (答复落不到槽位) 不上前台 —— 只说人话 (上一轮在等什么 / 这轮对不上)。
            // 内部术语与理由仍进遥测 (plan_resume.reason), 不消失也不静默。
            var verdict = agent.intent.PlanResumeService.HumanizeVoidNotice(cand.PendingQuestion, applyWhy) + "\n";
            agent.config.AgentTelemetry.Emit("plan_resume", "IndustrialAgentV2",
                ("plan_id", cand.Plan.PlanId), ("resumed", false), ("reason", applyWhy),
                ("fallthrough", PlanResumeFallthrough()));
            if (PlanResumeFallthrough())
            {
                // R457 链机制: 答复落不到槽位 ⇒ 作废检查点后**同轮转正常任务路径**, 不整轮吃掉。
                // 不伪造仍成立: 检查点已清, 不会拿旧产出凑答案。
                _resumeVoidNotice = verdict;
                return false;
            }
            response.Success = false;
            response.Content = verdict + "要接着上一轮, 就把答复写成完整任务再说一次; 否则直接给新任务即可。";
            return true;
        }

        // 续跑: 重建 ctx (真产出注入) → 从 seedRun 继续 (Completed 节点不重跑)
        var ctx = agent.intent.PlanRunner.NewContext(
            sessionId: message.SessionId, sourceText: cand.SourceText ?? message.Content);
        foreach (var kv in cand.NodeOutputs)
            ctx.NodeOutputs[kv.Key] = kv.Value;
        _planRunner ??= new agent.intent.PlanRunner();
        _planCtx = ctx;
        _lastPlan = cand.Plan;

        var run = await _planRunner.RunAsync(cand.Plan, ctx, ct,
            localFirst: null, remoteWindow: null, seedRun: cand.Run);
        _lastPlanRun = run;

        agent.config.AgentTelemetry.Emit("plan_resume", "IndustrialAgentV2",
            ("plan_id", cand.Plan.PlanId), ("resumed", true), ("state", run.State.ToString()),
            ("nodes", cand.Plan.Nodes.Count), ("waits", run.Waits.Count),
            ("seeded_outputs", cand.NodeOutputs.Count),
            ("slot", string.Join(",", cand.AwaitingParameterNames)));

        response.Success = run.State == TaskPlanRunState.Finished;
        response.Content = RenderResumeReply(cand, run);
        response.Data = new Dictionary<string, object>
        {
            { "planResumed", true },
            { "planId", cand.Plan.PlanId },
            { "planState", run.State.ToString() },
            { "awaitingNode", cand.AwaitingNodeId },
        };

        if (run.State == TaskPlanRunState.Finished)
            store.Clear(message.SessionId); // 跑完不留悬空的续跑入口
        else
            agent.intent.PlanResumeService.Capture(store, message.SessionId, cand.Plan, run, ctx.NodeOutputs, cand.SourceText);
        return true;
    }

    /// <summary>续跑答复渲染 (零 LLM): 节点结果 + 等待台账 (等待时长含用户思考时间, 是真账不是估计)。</summary>
    private static string RenderResumeReply(agent.intent.PlanResumeCandidate cand, TaskPlanRun run)
    {
        var sb = new System.Text.StringBuilder();
        sb.Append("🔄 续跑计划 ").Append(cand.Plan.PlanId)
          .Append(" (答复落到参数槽: ").Append(string.Join(",", cand.AwaitingParameterNames)).Append(')');
        if (!string.IsNullOrEmpty(cand.PendingQuestion))
            sb.Append("\n上一轮的问题: ").Append(Truncate(cand.PendingQuestion, 100));
        sb.Append('\n');
        foreach (var o in run.Outcomes)
            sb.Append("- ").Append(o.NodeId).Append(" [").Append(o.Location).Append("] ")
              .Append(o.State).Append(": ").Append(Truncate(o.Detail ?? string.Empty, 90)).Append('\n');
        if (run.Waits.Count > 0)
        {
            var now = agent.intent.Monotonic.NowUs();
            var totalMs = run.Waits.Values.Sum(w => ((w.EndedUs ?? now) - w.StartedUs) / 1000);
            sb.Append("等待台账: ").Append(run.Waits.Count).Append(" 条, 共 ").Append(totalMs)
              .Append("ms (含你思考的时间; 等待不占并发额度)").Append('\n');
        }
        sb.Append("计划状态: ").Append(run.State);
        return sb.ToString();
    }

    /// <summary>D4: 远程窗口起点 (计划构建时刻; 用于 "本地先行与远程等待真重叠" 测量)</summary>
    private long _planRemoteStartUs;

    /// <summary>D4: 远程窗口终点 (本轮产物/正文就绪时刻)</summary>
    private long _planRemoteReadyUs;

    /// <summary>计划真执行体 (v0.22.0 exp9 D3; DI 注入失效时回退默认实现 — 有台账才能拿到产物路径)</summary>
    private agent.intent.PlanRunner? _planRunner;

    private async Task<string> RunEvidenceGateAsync(
        Message message, IReadOnlyList<IntentDecomposer.SubTask> subTasks, CancellationToken ct)
    {
        if (_promptService == null || subTasks.Count == 0)
            return string.Empty;
        try
        {
            var gate = new agent.registry.EvidenceGate(facts: _continuationFacts);
            var verdict = gate.Evaluate(subTasks);
            // v0.11.0: evidence gate 打点 (问询触发率对比数据)
            agent.config.AgentTelemetry.Emit("evidence_gate", "IndustrialAgentV2",
                ("subtasks", subTasks.Count),
                ("suspects", subTasks.Count(t => t.Confidence < 0.60)),
                ("to_ask", verdict.ToAsk.Count),
                ("confidences", string.Join(",", subTasks.Select(t => Math.Round(t.Confidence, 2)))));
            if (verdict.ToAsk.Count == 0)
                return string.Empty;

            // 批量问询: 同组问题一次给出 (组=子任务), 符合"按内部分组直接给出多个或一个"铁律
            var prefs = new agent.registry.ClarificationPreferenceStore(_dataStoragePath);
            var answers = new List<string>();
            foreach (var req in verdict.ToAsk)
            {
                if (req.Questions.Count == 0)
                    continue;
                var batch = await agent.registry.ClarificationBatch.AskAsync(
                    _promptService, $"EvidenceGate/{req.SubTask.Intent}", req.Questions,
                    preferences: prefs, ct: ct);
                foreach (var a in batch.Answers)
                {
                    if (a.Answered && !string.IsNullOrWhiteSpace(a.Value))
                        answers.Add($"{a.Item.Question} → {a.Value}");
                }
            }
            return answers.Count > 0 ? string.Join("; ", answers) : string.Empty;
        }
        catch (OperationCanceledException) { throw; }
        catch (Exception ex)
        {
            // 问询链故障绝不阻断主流程 (降级: 带疑问直接执行, 与无 v7.14 行为一致)
            _logger.LogWarning(ex, "EvidenceGate 问询失败, 降级为直接执行");
            return string.Empty;
        }
    }

    /// <summary>R302: 数据源选择 + K1 全隔离 (env AGENTFRAMEWORK_K1_FULL_ISOLATION=1 → 剔除画像回流源)。</summary>
    private HashSet<DataSourceType> BuildEnabledSources(
        IReadOnlyList<IntentDecomposer.SubTask> subTasks, string intent)
    {
        var sources = subTasks.Count > 1
            ? new HashSet<DataSourceType>(IntentDecomposer.AggregateSources(subTasks))
            : new HashSet<DataSourceType>(IntentSourceMapping.GetSources(intent));
        if (Environment.GetEnvironmentVariable("AGENTFRAMEWORK_K1_FULL_ISOLATION") == "1")
        {
            sources.Remove(DataSourceType.Memory);
            sources.Remove(DataSourceType.Session);
            sources.Remove(DataSourceType.UserTendency);
            sources.Remove(DataSourceType.FixMemory); // v0.14.0: 自审修法记忆属经验注入, K1 对照实验须剔除
            agent.config.AgentTelemetry.Emit("k1_isolation", "IndustrialAgentV2",
                ("remaining", string.Join(",", sources)));
        }
        return sources;
    }
}
