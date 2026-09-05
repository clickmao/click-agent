using agent.intent;
using agent.userinteraction;

namespace agent.registry;

/// <summary>单个节点的执行结果</summary>
/// <summary>失败种类 (v7.15 重试策略): 决定节点失败是否值得重试。</summary>
public enum NodeFailureKind
{
    /// <summary>未失败</summary>
    None,

    /// <summary>瞬态失败 (网络/超时/LLM 5xx) — 可重试 (默认保守分类)</summary>
    Transient,

    /// <summary>永久失败 (参数校验/敏感拒绝/逻辑错误) — 重试无意义</summary>
    Permanent,
}

public class NodeExecutionResult
{
    public string NodeId { get; init; } = string.Empty;

    public PlanNodeState FinalState { get; init; }

    /// <summary>节点产物 (当前版本 = LLM 响应文本; 后续接真实 handler)</summary>
    public string? Output { get; init; }

    public string? Error { get; init; }

    /// <summary>失败种类 (v7.15): 默认 Transient — nodeRunner 实现方负责细分, Unknown 按可重试处理</summary>
    public NodeFailureKind FailureKind { get; init; } = NodeFailureKind.Transient;
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
        ClarificationPreferenceStore? preferences = null,
        IUserPromptService? prompts = null)
    {
        _nodeRunner = nodeRunner;
        _evidenceGate = evidenceGate ?? new EvidenceGate();
        _preferences = preferences;
        _prompts = prompts;
    }

    private readonly IUserPromptService? _prompts;

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

        // ── 层批调度 (v7.15 并发化): 同 Level 批内并发, 跨层顺序等待 ──
        // 依赖正确性由 Level 计算保证 (批内节点互不依赖); 单节点批走串行路径零行为变化。
        foreach (var levelGroup in order.GroupBy(n => n.Level).OrderBy(g => g.Key))
        {
            var batch = levelGroup.ToList();

            // 层边界: 检查用户插入的强制指令 (保持层粒度, 不在并发内轮询)
            var layerInjection = pollInjections?.Invoke();
            if (layerInjection != null && layerInjection.Kind == InjectedInstructionKind.Cancel)
            {
                run.State = TaskPlanRunState.Cancelled;
                run.PauseReason = $"用户插入停止指令: {layerInjection.Text}";
                SkipRemaining(order, run.NodeStates, batch[0].Id);
                return run;
            }

            // 依赖未完成 (前层失败/被跳过) → 本层全部连带跳过
            if (batch.All(n => n.DependsOn.Any(d =>
                    run.NodeStates.TryGetValue(d, out var s) &&
                    s is PlanNodeState.Failed or PlanNodeState.Skipped)) &&
                batch.Any(n => n.DependsOn.Count > 0))
            {
                foreach (var n in batch)
                    run.NodeStates[n.Id] = PlanNodeState.Skipped;
                continue;
            }

            // 层内预检: 敏感节点 → 暂停等审批 (先跑完已启动的非敏感语义不在本层发生 — 保守起步)
            var sensitive = batch.FirstOrDefault(n => InjectedInstructionClassifier.IsSensitiveIntent(n.Intent));
            if (sensitive != null)
            {
                run.State = TaskPlanRunState.PausedForApproval;
                run.PendingSensitiveNodeId = sensitive.Id;
                run.PauseReason = $"敏感任务「{sensitive.Text}」({sensitive.Intent}) 等待审批";
                run.NodeStates[sensitive.Id] = PlanNodeState.AwaitingApproval;
                return run;
            }

            // 问询未答节点: 编排层驱动批量问询 (不进并发批 — 问询有用户交互不能并行)
            var executable = new List<PlanNode>();
            foreach (var node in batch)
            {
                if (!node.IsExecutable)
                {
                    if (_prompts != null && await TryAskNodeClarificationsAsync(node, run, ct))
                        executable.Add(node);
                    else
                        run.NodeStates[node.Id] = PlanNodeState.AwaitingClarification;
                }
                else
                {
                    executable.Add(node);
                }
            }
            if (executable.Count == 0)
                continue;

            // 执行: 单节点串行 (零行为变化); 多节点按 MaxParallelism 分片并发
            if (executable.Count == 1 || plan.MaxParallelism <= 1)
            {
                var verdict = await RunNodeCoreAsync(executable[0], order, run, plan, ct);
                if (verdict != null)
                    return verdict; // Cancelled / FailFast 终止
            }
            else
            {
                var stopped = false;
                foreach (var shard in executable.Chunk(plan.MaxParallelism))
                {
                    var results = await Task.WhenAll(
                        shard.Select(n => RunNodeCoreAsync(n, order, run, plan, ct)));
                    var stop = results.FirstOrDefault(v => v != null);
                    if (stop != null)
                    {
                        // Cancelled / FailFast: 本批已全部落终态 (WhenAll 等待), 终止计划
                        run.State = stop.State;
                        run.PauseReason = stop.PauseReason;
                        stopped = true;
                        break;
                    }
                }
                if (stopped)
                    return run;
            }
        }

        run.State = TaskPlanRunState.Finished;
        return run;
    }

    /// <summary>
    /// 单节点核心执行 (预检已完成): 置 Running → nodeRunner → 落终态。
    /// 返回 null = 继续; 返回非 null = 计划终止 (Cancelled/Finished), 调用方直接 return。
    /// 并发注意: 只写本节点状态与 run 终态字段, 不碰其他节点 — 批内节点互不依赖, 状态字典写入不冲突。
    /// </summary>
    private async Task<TaskPlanRun?> RunNodeCoreAsync(
        PlanNode node, List<PlanNode> order, TaskPlanRun run, TaskPlan plan, CancellationToken ct)
    {
        run.NodeStates[node.Id] = PlanNodeState.Running;

        // ── FailRetry (v7.15): 瞬态失败按 MaxRetries 重试 (指数退避 500ms×2^n 上限 4s), 耗尽才收敛 ──
        var maxRetries = node.MaxRetries ?? plan.DefaultMaxRetries;
        NodeExecutionResult result;
        var attempt = 0;
        while (true)
        {
            try
            {
                result = await _nodeRunner(node, ct);
            }
            catch (OperationCanceledException)
            {
                // 取消永不重试 (B.3 约束 2)
                run.NodeStates[node.Id] = PlanNodeState.Skipped;
                run.State = TaskPlanRunState.Cancelled;
                return run;
            }

            var retryable = result.FinalState == PlanNodeState.Failed &&
                            result.FailureKind != NodeFailureKind.Permanent &&
                            attempt < maxRetries;
            if (!retryable)
                break;

            var waitMs = Math.Min(500 * (1 << attempt), 4000);
            run.Retries.Add(new NodeRetryRecord
            {
                NodeId = node.Id,
                Attempt = attempt + 1,
                Error = result.Error,
                WaitedMs = waitMs,
            });
            try
            {
                await Task.Delay(waitMs, ct);
            }
            catch (OperationCanceledException)
            {
                // 重试等待中取消 → 立即返回 Cancelled (B.4-4)
                run.NodeStates[node.Id] = PlanNodeState.Skipped;
                run.State = TaskPlanRunState.Cancelled;
                return run;
            }
            attempt++;
        }

        run.NodeStates[node.Id] = result.FinalState;
        if (result.FinalState == PlanNodeState.Failed)
        {
            // 重试耗尽/永久失败 → 原有 FailFast 收敛语义 (下游 Skipped + 计划 Finished)
            var retriedNote = attempt > 0 ? $" (已重试 {attempt} 次)" : string.Empty;
            run.PauseReason = $"节点「{node.Text}」失败{retriedNote}: {result.Error}";
            SkipRemaining(order, run.NodeStates, node.Id);
            run.State = TaskPlanRunState.Finished;
            return run;
        }
        return null;
    }

    /// <summary>
    /// 对单个节点的待澄清条目跑一轮批量问询 (v7.13.2 编排接线):
    /// 按问询协议分组打包 → 用户一次回答全部 → 合法答案写回参数槽 (Name 匹配) 并移除已答条目。
    /// 返回 true = 该节点已可执行 (Clarifications 清空)。
    /// </summary>
    private async Task<bool> TryAskNodeClarificationsAsync(PlanNode node, TaskPlanRun run, CancellationToken ct)
    {
        var groups = ClarificationBatch.Group(node.Clarifications);
        var allAnswered = true;
        foreach (var group in groups)
        {
            var result = await ClarificationBatch.AskAsync(
                _prompts!, $"任务「{node.Text}」参数确认", group,
                preferences: _preferences, ct: ct);
            if (!result.AllAnswered)
                allAnswered = false;
            foreach (var ans in result.Answers)
            {
                if (!ans.Answered)
                    continue;
                // 答案落地: 同名参数槽写值; 没有对应参数槽的答案 (证据补充类) 挂到节点文本说明
                var slot = node.Parameters.FirstOrDefault(p2 =>
                    string.Equals(p2.Name, ans.Item.ParameterName, StringComparison.OrdinalIgnoreCase));
                if (slot != null)
                    slot.Value = ans.Value;
                node.Clarifications.Remove(ans.Item);
            }
        }
        if (!allAnswered)
            run.PauseReason = $"节点「{node.Text}」部分参数未确认, 继续等待澄清";
        return node.IsExecutable;
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
