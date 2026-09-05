using agent.intent;

namespace agent.registry;

/// <summary>单个节点的执行结果</summary>
public class NodeExecutionResult
{
    public string NodeId { get; init; } = string.Empty;

    public PlanNodeState FinalState { get; init; }

    /// <summary>节点产物 (当前版本 = LLM 响应文本; 后续接真实 handler)</summary>
    public string? Output { get; init; }

    public string? Error { get; init; }
}

/// <summary>
/// 逐子任务顺序调度引擎 (v7.11): TaskPlan → 拓扑序逐个执行。
/// 顺序调度保证依赖正确性; 同层并行留给并发化迭代 (先保正确, 再提速)。
/// 敏感意图节点默认暂停全计划等待审批 (PausedForApproval 不可跳过)。
/// </summary>
public class TaskPlanExecutor
{
    private readonly Func<PlanNode, CancellationToken, Task<NodeExecutionResult>> _nodeRunner;
    private readonly EvidenceGate _evidenceGate;
    private readonly ClarificationPreferenceStore? _preferences;

    /// <summary>
    /// nodeRunner: 节点执行委托 (由宿主注入真实执行体 — LLM 调用/handler 分发)。
    /// 引擎只管调度语义, 不绑定具体执行方式。
    /// </summary>
    /// <param name="nodeRunner">节点执行体</param>
    /// <param name="evidenceGate">证据门槛 (v7.13): 低置信节点执行前先裁定, 默认开启 (疑问上限 3)</param>
    /// <param name="preferences">问询偏好库 (v7.13): 非空时批量问询自动复用历史偏好并回写</param>
    public TaskPlanExecutor(
        Func<PlanNode, CancellationToken, Task<NodeExecutionResult>> nodeRunner,
        EvidenceGate? evidenceGate = null,
        ClarificationPreferenceStore? preferences = null)
    {
        _nodeRunner = nodeRunner;
        _evidenceGate = evidenceGate ?? new EvidenceGate();
        _preferences = preferences;
    }

    /// <summary>
    /// 执行计划: 拓扑序逐节点。
    /// pollInjections: 每个节点边界轮询用户插入指令 (返回最新一条或 null) —
    /// Cancel 指令立即终止计划, 未完成节点标记 Skipped。
    /// </summary>
    public async Task<TaskPlanRun> ExecuteAsync(
        TaskPlan plan,
        Func<InjectedInstruction?>? pollInjections = null,
        CancellationToken ct = default)
    {
        var run = new TaskPlanRun { PlanId = plan.PlanId };
        foreach (var n in plan.Nodes)
            run.NodeStates[n.Id] = PlanNodeState.Pending;

        // 拓扑序: 层级优先, 同层保持用户表达顺序 (数组序=拆解序, 不是文本长度)
        var indexOf = plan.Nodes.Select((n, i) => (n.Id, i)).ToDictionary(x => x.Id, x => x.i);
        var order = plan.Nodes.OrderBy(n => n.Level).ThenBy(n => indexOf[n.Id]).ToList();

        // ── 证据门槛裁定 (v7.13): 执行前对全计划跑一次 EvidenceGate ──
        //   低置信节点 (Confidence < 阈值) → 生成证据补充问题 (按优先级, 受最大疑问数限制)
        //   裁定结果回写节点: Questions 进 Clarifications → IsExecutable=false → AwaitingClarification
        //   超限节点 (DroppedForLimit) → 走 SuggestedValues 兜底, 不静默不编造
        //   已有 Clarifications 的节点不重复裁定 (问询协议不叠加)
        var gateVerdict = _evidenceGate.Evaluate(
            order.Select(n => new IntentDecomposer.SubTask(
                n.Text, n.Intent, DependsOnPrevious: n.DependsOn.Count > 0, Order: indexOf[n.Id],
                Relation: IntentDecomposer.TaskRelation.None,
                Confidence: n.Confidence, Flags: n.ConfidenceFlags)).ToList());

        foreach (var req in gateVerdict.ToAsk)
        {
            var node = order[req.SubTask.Order]; // Order 即拆解序 = 数组序 (order 按 ThenBy(indexOf) 排列)
            if (node.Clarifications.Count > 0)
                continue;
            foreach (var q in req.Questions)
            {
                if (node.Clarifications.Any(x => x.ParameterName == q.ParameterName))
                    continue;
                q.NodeId = node.Id;
                node.Clarifications.Add(q);
            }
        }

        // 超限兜底: 问不了的低置信节点用 SuggestedValues 预填参数槽缺失值说明 (不伪造答案, 只挂提示)
        foreach (var dropped in gateVerdict.DroppedForLimit)
        {
            var node = order[dropped.Order];
            run.DroppedForEvidenceLimit.Add(node.Id);
        }

        // 偏好预排 (v7.13): 有历史偏好的澄清条目 → SuggestedValues/选项序预排 (同类问题不重复问)
        if (_preferences != null)
            foreach (var node in order)
                foreach (var cl in node.Clarifications)
                    _preferences.ApplyTo(cl);

        foreach (var node in order)
        {
            // 节点边界: 检查用户插入的强制指令
            var injection = pollInjections?.Invoke();
            if (injection != null && injection.Kind == InjectedInstructionKind.Cancel)
            {
                run.State = TaskPlanRunState.Cancelled;
                run.PauseReason = $"用户插入停止指令: {injection.Text}";
                SkipRemaining(order, run.NodeStates, node.Id);
                return run;
            }

            // 依赖未完成 (前序失败/被跳过) → 本节点连带跳过
            var failedDep = node.DependsOn
                .Any(d => run.NodeStates.TryGetValue(d, out var s) &&
                          s is PlanNodeState.Failed or PlanNodeState.Skipped);
            if (failedDep)
            {
                run.NodeStates[node.Id] = PlanNodeState.Skipped;
                continue;
            }

            // 敏感意图 → 全计划暂停等审批 (优先于澄清: 敏感节点连参数带执行都需审批)
            if (InjectedInstructionClassifier.IsSensitiveIntent(node.Intent))
            {
                run.State = TaskPlanRunState.PausedForApproval;
                run.PendingSensitiveNodeId = node.Id;
                run.PauseReason = $"敏感任务「{node.Text}」({node.Intent}) 等待审批";
                run.NodeStates[node.Id] = PlanNodeState.AwaitingApproval;
                return run;
            }

            // 问询未答 → 保持等待 (不阻断后续无关节点)
            if (!node.IsExecutable)
            {
                run.NodeStates[node.Id] = PlanNodeState.AwaitingClarification;
                continue;
            }

            run.NodeStates[node.Id] = PlanNodeState.Running;
            NodeExecutionResult result;
            try
            {
                result = await _nodeRunner(node, ct);
            }
            catch (OperationCanceledException)
            {
                run.NodeStates[node.Id] = PlanNodeState.Skipped;
                run.State = TaskPlanRunState.Cancelled;
                return run;
            }

            run.NodeStates[node.Id] = result.FinalState;
            if (result.FinalState == PlanNodeState.Failed)
            {
                // FailFast: 单节点失败停止计划 (重试策略后续迭代)
                run.PauseReason = $"节点「{node.Text}」失败: {result.Error}";
                SkipRemaining(order, run.NodeStates, node.Id);
                run.State = TaskPlanRunState.Finished;
                return run;
            }
        }

        run.State = TaskPlanRunState.Finished;
        return run;
    }

    private static void SkipRemaining(IEnumerable<PlanNode> order, Dictionary<string, PlanNodeState> states, string stoppedAtId)
    {
        var seen = false;
        foreach (var n in order)
        {
            if (n.Id == stoppedAtId)
            {
                seen = true;
                continue;
            }
            if (seen && states[n.Id] == PlanNodeState.Pending)
                states[n.Id] = PlanNodeState.Skipped;
        }
    }
}
