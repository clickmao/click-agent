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

    /// <summary>
    /// 执行**中途**发现的运行时依赖 (v0.22.0 exp9 D7): 本节点需要该节点的产出才能继续。
    /// 配 FinalState=Waiting 返回 ⇒ 调度器记账等待, 生产节点就绪后**重跑本节点**(此时依赖已注入)。
    /// 不允许用它来"要一个不存在的节点": 未知 id 按 Pending 处理 → 收尾轮如实失败。
    /// </summary>
    public string? NeedNodeId { get; init; }
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
    /// <param name="prompts">问询服务 (v7.13): 非空时对可澄清节点驱动批量问询</param>
    /// <param name="checkpointStore">检查点库 (需求3): 每层批/终态快照</param>
    /// <param name="checkpointSessionId">检查点会话 Id (空 = 不落盘)</param>
    /// <param name="onWait">运行时依赖等待回调 (v0.22.0 exp9 D7): (节点, 生产节点 Id, 原因) → 事件出口。
    /// 回调抛异常**不得**打断计划 (与 D5 同一纪律); null = 无事件出口 (旧行为不变)。</param>
    /// <param name="maxWaitMs">单次运行时依赖等待上限 (D7 有界等待; 超限如实失败, 不许无限空耗)</param>
    public TaskPlanExecutor(
        Func<PlanNode, CancellationToken, Task<NodeExecutionResult>> nodeRunner,
        EvidenceGate? evidenceGate = null,
        ClarificationPreferenceStore? preferences = null,
        IUserPromptService? prompts = null,
        agent.recovery.CheckpointStore? checkpointStore = null,
        string checkpointSessionId = "",
        Func<PlanNode, string, string, CancellationToken, Task>? onWait = null,
        long maxWaitMs = 600_000)
    {
        _nodeRunner = nodeRunner;
        _evidenceGate = evidenceGate ?? new EvidenceGate();
        _preferences = preferences;
        _prompts = prompts;
        _checkpoints = checkpointStore;
        _checkpointSessionId = checkpointSessionId;
        _onWait = onWait;
        _maxWaitMs = maxWaitMs;
        _maxWaitUs = maxWaitMs * 1000L;
    }

    private readonly Func<PlanNode, string, string, CancellationToken, Task>? _onWait;
    private readonly long _maxWaitMs;
    private readonly long _maxWaitUs;

    private readonly agent.recovery.CheckpointStore? _checkpoints;
    private readonly string _checkpointSessionId;

    /// <summary>
    /// 检查点落盘 (需求3): 每层批结束/计划终态时保存节点状态快照。
    /// store 未注入或 sessionId 为空 → 零开销跳过 (旧行为不变)。
    /// </summary>
    private void SaveCheckpoint(TaskPlanRun run)
    {
        if (_checkpoints is null || string.IsNullOrEmpty(_checkpointSessionId))
            return;
        _checkpoints.Save(new agent.recovery.ExecutionCheckpoint
        {
            SessionId = _checkpointSessionId,
            PlanId = run.PlanId,
            RunId = run.RunId,
            NodeStates = run.NodeStates.ToDictionary(
                kv => kv.Key, kv => kv.Value.ToString(), StringComparer.Ordinal),
            LastCompletedNodeId = run.NodeStates
                .Where(kv => kv.Value == PlanNodeState.Completed)
                .Select(kv => kv.Key)
                .LastOrDefault(),
            PauseReason = run.PauseReason,
        });
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
        CancellationToken ct = default,
        TaskPlanRun? seedRun = null)
    {
        // D7b 续跑: seedRun 非空 = 从检查点重建的运行态继续跑 (节点状态/等待台账/暂停原因都是上一轮的)
        var run = seedRun ?? new TaskPlanRun { PlanId = plan.PlanId };
        if (seedRun is null)
        {
            foreach (var n in plan.Nodes)
                run.NodeStates[n.Id] = PlanNodeState.Pending;
        }
        else
        {
            // 续跑状态归一: 已 Completed 的**不重跑** (产出已在 ctx.NodeOutputs 里, 重跑=重复副作用);
            // 半途态 (等待/等用户/运行中) 一律转 Pending, 本轮重新参与调度。
            foreach (var n in plan.Nodes)
            {
                if (!run.NodeStates.TryGetValue(n.Id, out var st))
                    run.NodeStates[n.Id] = PlanNodeState.Pending;
                else if (st is PlanNodeState.AwaitingClarification or PlanNodeState.AwaitingApproval
                         or PlanNodeState.Waiting or PlanNodeState.Running)
                    run.NodeStates[n.Id] = PlanNodeState.Pending;
            }

            run.State = TaskPlanRunState.Running;
            run.PauseReason = null;
        }

        // 拓扑序: 层级优先, 同层保持用户表达顺序 (数组序=拆解序, 不是文本长度)
        var indexOf = plan.Nodes.Select((n, i) => (n.Id, i)).ToDictionary(x => x.Id, x => x.i);
        var order = plan.Nodes.OrderBy(n => n.Level).ThenBy(n => indexOf[n.Id]).ToList();

        // D7: 等别人产出的节点 (本层不跑, 记账; 生产节点落终态后由唤醒轮次执行)
        var deferred = new List<PlanNode>();

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
            if (node.Clarifications.Count > 0 || node.ClarificationsSettled) // D7b: 已答复过的澄清不再重复问
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
            // D7b 续跑: 上一轮已 Completed 的节点不再重跑 (产出已注入 ctx.NodeOutputs; 重跑 = 重复副作用)。
            // 注意 order 保持完整 —— 生产节点查找/依赖判定仍要看得见它们。
            var batch = seedRun is null
                ? levelGroup.ToList()
                : levelGroup.Where(n => StateOf(run, n.Id) != PlanNodeState.Completed).ToList();

            // 层边界: 检查用户插入的强制指令 (保持层粒度, 不在并发内轮询)
            var layerInjection = pollInjections?.Invoke();
            if (layerInjection != null && layerInjection.Kind == InjectedInstructionKind.Cancel)
            {
                run.State = TaskPlanRunState.Cancelled;
                run.PauseReason = $"用户插入停止指令: {layerInjection.Text}";
                SkipRemaining(order, run.NodeStates, batch[0].Id);
                SaveCheckpoint(run);
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
                SaveCheckpoint(run);
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

            // ── D7 运行时依赖预判: 需要别人产出而对方未就绪的节点本层不跑 → 记账等待 (不占并发额度) ──
            var ready = new List<PlanNode>();
            foreach (var node in executable)
            {
                var paused = await PrepareRuntimeDepsAsync(node, order, run, ct);
                if (paused != null)
                {
                    SaveCheckpoint(run);
                    return paused;
                }
                if (run.NodeStates[node.Id] == PlanNodeState.Waiting)
                {
                    deferred.Add(node);
                    continue;
                }
                ready.Add(node);
            }

            // 执行: 单节点串行 (零行为变化); 多节点按 MaxParallelism 分片并发
            if (ready.Count == 1 || plan.MaxParallelism <= 1)
            {
                var verdict = await RunNodeCoreAsync(ready[0], order, run, plan, ct);
                if (verdict != null)
                {
                    ResolveDeferredOnTermination(deferred, run); // 等待中的节点必须明确落终态 (不留悬空 Waiting)
                    return verdict; // Cancelled / FailFast 终止
                }
                if (run.NodeStates[ready[0].Id] == PlanNodeState.Waiting)
                    deferred.Add(ready[0]);
            }
            else if (ready.Count > 0)
            {
                var stopped = false;
                foreach (var shard in ready.Chunk(plan.MaxParallelism))
                {
                    var results = await Task.WhenAll(
                        shard.Select(n => RunNodeCoreAsync(n, order, run, plan, ct)));
                    var stop = results.FirstOrDefault(v => v != null);
                    foreach (var n in shard)
                        if (run.NodeStates[n.Id] == PlanNodeState.Waiting)
                            deferred.Add(n);
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
                {
                    ResolveDeferredOnTermination(deferred, run);
                    SaveCheckpoint(run);
                    return run;
                }
            }

            // 层批完成 → 唤醒可跑的等待节点 (D7) → 检查点 (需求3: 每层粒度复原)
            var drainVerdict = await DrainWaitsAsync(order, run, plan, deferred, ct);
            if (drainVerdict != null)
            {
                SaveCheckpoint(run);
                return drainVerdict;
            }
            SaveCheckpoint(run);
        }

        // D7 收尾: 全部层跑完后仍未唤醒的等待节点 —— 生产节点此时必然已落终态 (FailFast 会把未跑的标 Skipped),
        // 所以这里要么唤醒执行, 要么**如实失败**; 绝不留"永远在等"的假状态。
        var tailVerdict = await DrainWaitsAsync(order, run, plan, deferred, ct, finalPass: true);
        if (tailVerdict != null)
        {
            SaveCheckpoint(run);
            return tailVerdict;
        }

        run.State = TaskPlanRunState.Finished;
        SaveCheckpoint(run);
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

        // D7: 执行体**中途**才发现需要别的节点产出 (result.NeedNodeId)。
        //     ① 依赖已就绪 → 注入依赖并**立即重跑** (不空等);
        //     ② 依赖未就绪 → 记账等待 (MarkWaiting), 交层批后的唤醒轮次重跑;
        //     ③ 重复索要已注入的依赖 → 如实失败 (防无限重跑, 不静默吞)。
        var reinjections = 0;
        while (result.FinalState == PlanNodeState.Waiting
               && !string.IsNullOrEmpty(result.NeedNodeId)
               && reinjections < 2)
        {
            var pid = result.NeedNodeId!;
            if (StateOf(run, pid) != PlanNodeState.Completed)
                break; // 未就绪 → 走下面的等待分支

            if (node.RuntimeDeps.Contains(pid, StringComparer.Ordinal))
            {
                result = new NodeExecutionResult
                {
                    NodeId = node.Id,
                    FinalState = PlanNodeState.Failed,
                    FailureKind = NodeFailureKind.Permanent,
                    Error = $"执行体重复索要已注入的依赖产出 ({pid})",
                };
                break;
            }

            AddRuntimeDep(node, pid);
            try
            {
                result = await _nodeRunner(node, ct).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                run.NodeStates[node.Id] = PlanNodeState.Skipped;
                run.State = TaskPlanRunState.Cancelled;
                return run;
            }
            reinjections++;
        }

        if (result.FinalState == PlanNodeState.Waiting && !string.IsNullOrEmpty(result.NeedNodeId))
        {
            var pid = result.NeedNodeId!;
            var pstate = StateOf(run, pid);
            var reason = pstate switch
            {
                PlanNodeState.AwaitingClarification or PlanNodeState.AwaitingApproval => "user",
                PlanNodeState.Running => "running",
                _ => "queued",
            };
            MarkWaiting(node, pid, reason, run);
            await NotifyWaitAsync(node, pid, reason, ct).ConfigureAwait(false);
            return null;
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

    // ───────────────────────────── v0.22.0 exp9 D7: 运行时依赖等待 ─────────────────────────────

    /// <summary>
    /// D7 预判: 节点需要别人的产出而对方未就绪 ⇒ 记账等待 (状态=Waiting, 本层不跑; 由唤醒轮次重跑);
    /// 返回非 null = 计划本轮到此为止 (生产节点在等用户 ⇒ 谁也拿不到数据, 不许伪造硬跑)。
    /// </summary>
    private async Task<TaskPlanRun?> PrepareRuntimeDepsAsync(
        PlanNode node, List<PlanNode> order, TaskPlanRun run, CancellationToken ct)
    {
        var producerId = RuntimeDependencyScanner.FindProducer(node, order);
        if (producerId is null)
            return null;

        if (CreatesWaitCycle(run, node.Id, producerId))
            return FailPlan(node, run, order,
                $"运行时依赖成环: 「{node.Text}」等 {producerId}, 而 {producerId} 又在等它 (死锁已拒)");

        var state = StateOf(run, producerId);
        switch (state)
        {
            case PlanNodeState.Completed:
                AddRuntimeDep(node, producerId);
                return null;

            case PlanNodeState.Failed:
            case PlanNodeState.Skipped:
                return FailPlan(node, run, order,
                    $"运行时依赖节点 {producerId} 未成功 ({state}) — 不静默兜底");

            case PlanNodeState.AwaitingClarification:
            case PlanNodeState.AwaitingApproval:
                MarkWaiting(node, producerId, "user", run);
                await NotifyWaitAsync(node, producerId, "user", ct).ConfigureAwait(false);
                run.State = TaskPlanRunState.PausedForDependency;
                run.PauseReason =
                    $"节点「{node.Text}」等待 {producerId} 的产出, 而 {producerId} 在等用户回复 (本轮不产出, 不伪造)";
                return run;

            default:
            {
                var reason = state == PlanNodeState.Running ? "running" : "queued";
                MarkWaiting(node, producerId, reason, run);
                await NotifyWaitAsync(node, producerId, reason, ct).ConfigureAwait(false);
                return null;
            }
        }
    }

    /// <summary>
    /// D7 唤醒轮次 (每层批结束后 + 计划收尾各跑一次): 生产节点已落终态的等待节点 → 注入依赖并**重跑**。
    /// 收尾轮 (finalPass) 不会再等到后续层, 所以"仍未产出"必须如实失败 —— 不许留假的"永远在等"。
    /// </summary>
    private async Task<TaskPlanRun?> DrainWaitsAsync(
        List<PlanNode> order, TaskPlanRun run, TaskPlan plan,
        List<PlanNode> deferred, CancellationToken ct, bool finalPass = false)
    {
        if (deferred.Count == 0)
            return null;

        foreach (var node in deferred.ToList())
        {
            if (!run.Waits.TryGetValue(node.Id, out var wait))
                continue;

            var state = StateOf(run, wait.ProducerId);

            // 有界等待: **先判上限** (含"产出迟到"的情形) —— 过了上限就不采用迟到产出, 如实失败。
            // 顺序很关键: 若先判 Completed, 上限对"等到了但太晚"永远不可达 = 假的边界。
            if (Monotonic.NowUs() - wait.StartedUs > _maxWaitUs)
            {
                wait.EndedUs = Monotonic.NowUs();
                deferred.Remove(node);
                return FailPlan(node, run, order,
                    $"等待 {wait.ProducerId} 产出超过上限 ({(wait.EndedUs - wait.StartedUs) / 1000}ms > {_maxWaitMs}ms) — 不采用迟到产出");
            }

            if (state == PlanNodeState.Completed)
            {
                wait.EndedUs = Monotonic.NowUs();
                AddRuntimeDep(node, wait.ProducerId);
                run.NodeStates[node.Id] = PlanNodeState.Pending; // 释放等待态 → 立刻可跑
                deferred.Remove(node);
                var verdict = await RunNodeCoreAsync(node, order, run, plan, ct).ConfigureAwait(false);
                if (verdict != null)
                    return verdict;
                if (run.NodeStates[node.Id] == PlanNodeState.Waiting)
                    deferred.Add(node); // 重跑中又发现新依赖 → 留在队列
                continue;
            }

            if (state is PlanNodeState.Failed or PlanNodeState.Skipped)
            {
                wait.EndedUs = Monotonic.NowUs();
                deferred.Remove(node);
                return FailPlan(node, run, order,
                    $"运行时依赖节点 {wait.ProducerId} 未成功 ({state}) — 不静默兜底");
            }

            if (state is PlanNodeState.AwaitingClarification or PlanNodeState.AwaitingApproval)
            {
                run.State = TaskPlanRunState.PausedForDependency;
                run.PauseReason =
                    $"节点「{node.Text}」等待 {wait.ProducerId} 的产出, 而 {wait.ProducerId} 在等用户回复 (本轮不产出, 不伪造)";
                return run;
            }

            if (finalPass)
            {
                wait.EndedUs = Monotonic.NowUs();
                deferred.Remove(node);
                return FailPlan(node, run, order,
                    $"运行时依赖 {wait.ProducerId} 在计划结束时仍未产出 (状态={state})");
            }
        }
        return null;
    }

    private static PlanNodeState StateOf(TaskPlanRun run, string nodeId)
        => run.NodeStates.TryGetValue(nodeId, out var s) ? s : PlanNodeState.Pending;

    /// <summary>
    /// 计划提前终止 (FailFast / Cancelled) 时仍在等待的节点必须**明确落终态** —— 不许留一个悬空的 Waiting:
    /// 生产节点成功不了 ⇒ 消费节点 Failed (依赖未产出, 不静默); 取消 ⇒ Skipped (既有取消语义)。
    /// </summary>
    private static void ResolveDeferredOnTermination(List<PlanNode> deferred, TaskPlanRun run)
    {
        if (deferred.Count == 0)
            return;
        var cancelled = run.State == TaskPlanRunState.Cancelled;
        var ids = new List<string>();
        foreach (var node in deferred)
        {
            if (run.Waits.TryGetValue(node.Id, out var w))
                w.EndedUs = w.EndedUs ?? Monotonic.NowUs();
            run.NodeStates[node.Id] = cancelled ? PlanNodeState.Skipped : PlanNodeState.Failed;
            ids.Add(node.Id);
        }
        run.PauseReason = (run.PauseReason is null ? "" : run.PauseReason + "; ")
            + $"{(cancelled ? "已取消" : "依赖未产出")}: {string.Join(",", ids)} 未执行 (不静默兜底)";
        deferred.Clear();
    }

    private static void MarkWaiting(PlanNode node, string producerId, string reason, TaskPlanRun run)
    {
        run.NodeStates[node.Id] = PlanNodeState.Waiting;
        run.Waits[node.Id] = new NodeWaitRecord(node.Id, producerId, reason, Monotonic.NowUs());
    }

    private static void AddRuntimeDep(PlanNode node, string producerId)
    {
        if (!node.RuntimeDeps.Contains(producerId, StringComparer.Ordinal))
            node.RuntimeDeps.Add(producerId);
    }

    /// <summary>
    /// 等待图无环校验: A 等 B, 而 B (或 B 等的…) 又在等 A ⇒ 死锁, 必须拒 (含自环)。
    /// 环只可能出现在"双方都还没跑"的情形, 所以判定必须发生在记账时, 不能等到超时。
    /// </summary>
    private static bool CreatesWaitCycle(TaskPlanRun run, string nodeId, string producerId)
    {
        var seen = new HashSet<string>(StringComparer.Ordinal) { nodeId };
        var cursor = producerId;
        while (cursor is not null)
        {
            if (!seen.Add(cursor))
                return true;
            cursor = run.Waits.TryGetValue(cursor, out var w) ? w.ProducerId : null;
        }
        return false;
    }

    /// <summary>等待事件出口 (D7): 回调异常一律吞掉 —— 事件出口不许打断计划 (与 D5 同一纪律)</summary>
    private async Task NotifyWaitAsync(PlanNode node, string producerId, string reason, CancellationToken ct)
    {
        if (_onWait is null)
            return;
        try
        {
            await _onWait(node, producerId, reason, ct).ConfigureAwait(false);
        }
        catch
        {
            // 事件出口失败不影响调度正确性
        }
    }

    /// <summary>依赖类失败收敛 (与 RunNodeCoreAsync 的 FailFast 语义一致: 下游 Skipped + 计划 Finished)</summary>
    private TaskPlanRun FailPlan(PlanNode node, TaskPlanRun run, List<PlanNode> order, string reason)
    {
        run.NodeStates[node.Id] = PlanNodeState.Failed;
        run.PauseReason = $"节点「{node.Text}」失败: {reason}";
        SkipRemaining(order, run.NodeStates, node.Id);
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
