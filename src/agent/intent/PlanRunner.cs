using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using agent.config;
using agent.registry;
using agent.skills;

namespace agent.intent;

/// <summary>
/// 计划真执行体 (v0.22.0 exp9 D3) —— 替换 v7.15 起的**哑执行体**。
///
/// 旧哑体 (IndustrialAgentV2 原文): 每个节点一律 `Skipped + Output=null`, 只为演练调度语义。
/// 本执行体的语义:
///   Local  → 真调本地执行器 (真子进程/真统计; 零 LLM 调用)
///   Hybrid → 远程正文已就绪, 本地立即处理 (同一节点第二段; 不新增 LLM 调用)
///   Remote → **不重复调用模型**: 主链已产出的正文即其产物; 未就绪则诚实标 Skipped
///
/// 反向断言 (D3 验收): 开启时**不得**再发 `plan_dummy_runner` 点位 —— 该点位只在闸门关闭的回退路径出现。
/// 闸门: `AGENTFRAMEWORK_PLAN_EXEC=0|false|off` 回退哑体 (同题对照用), 缺省开启。
/// </summary>
public sealed class PlanRunner
{
    /// <summary>回退哑体型 (闸门关闭时) 的打点点位 —— 出现即证明"哑体仍在用"</summary>
    public const string DummyRunnerPoint = "plan_dummy_runner";

    public const string EnableEnvName = "AGENTFRAMEWORK_PLAN_EXEC";

    private readonly Dictionary<string, ILocalNodeExecutor> _executors;
    private readonly PythonArtifactLedger? _ledger;
    private readonly Func<bool> _gate;
    private readonly IPlanEventSink? _events;

    public PlanRunner(
        IEnumerable<ILocalNodeExecutor>? executors = null,
        PythonArtifactLedger? ledger = null,
        Func<bool>? gate = null,
        IPlanEventSink? events = null)
    {
        var list = executors?.ToList() ?? [new PythonSelfTestExecutor(), new TextProcessExecutor(), new FormalVerifyExecutor()];
        _executors = list.ToDictionary(e => e.Id, StringComparer.Ordinal);
        _ledger = ledger;
        _gate = gate ?? (() => IsEnabled());
        _events = events;
    }

    /// <summary>计划真执行闸门 (缺省开; raw 为空时读环境变量。=0|false|off ⇒ 回退哑体)</summary>
    public static bool IsEnabled(string? raw = null)
    {
        var v = raw ?? Environment.GetEnvironmentVariable(EnableEnvName);
        if (string.IsNullOrWhiteSpace(v))
            return true;
        return !string.Equals(v, "0", StringComparison.OrdinalIgnoreCase)
            && !string.Equals(v, "false", StringComparison.OrdinalIgnoreCase)
            && !string.Equals(v, "off", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>已接线执行器 (诊断/前端显示用)</summary>
    public IReadOnlyCollection<string> WiredExecutors => _executors.Keys;

    /// <summary>
    /// 新建本地执行上下文 (D4: 计划构建时就用它启动本地先行; 产物就绪后再回填远程事实)。
    /// 为什么不复用 ContextFromLedger: 那一刻台账里最新产物是**上一轮**的 (陈旧), 回填会造假事实。
    /// </summary>
    public static LocalNodeContext NewContext(string? sessionId = null, string? sourceText = null,
        string? remoteText = null, string? artifactPath = null) => new()
        {
            SessionId = sessionId,
            SourceText = sourceText,
            RemoteText = remoteText,
            ArtifactPath = artifactPath,
        };

    /// <summary>产物就绪后, 把台账里最新产物路径回填到既有 ctx (同一对象 ⇒ 不丢本地先行节点的输出)</summary>
    public LocalNodeContext FillFromLedger(LocalNodeContext ctx)
    {
        var items = _ledger?.Snapshot();
        var latest = items is { Count: > 0 }
            ? items.OrderByDescending(r => r.AtUnixMs).FirstOrDefault()
            : null;
        ctx.ArtifactPath = latest?.Path;
        return ctx;
    }

    /// <summary>
    /// 从产物台账构造上下文 (取最近一条 python 报告 = 刚落盘的产物)。
    /// 诚实边界: 台账无会话维度, 跨会话并发时取"最新一条"; 会话级隔离属 D5。
    /// </summary>
    public LocalNodeContext ContextFromLedger(string? sessionId = null, string? remoteText = null,
        string? sourceText = null)
    {
        var items = _ledger?.Snapshot();
        var latest = items is { Count: > 0 }
            ? items.OrderByDescending(r => r.AtUnixMs).FirstOrDefault()
            : null;
        return new LocalNodeContext
        {
            SessionId = sessionId,
            ArtifactPath = latest?.Path,
            RemoteText = remoteText,
            SourceText = sourceText,
        };
    }

    /// <summary>
    /// 把"任务细分 + 每步执行位置"公告给前端 (D5)。调用时机 = 意图进入、模型还**没**开始生成时,
    /// 这样前端能立刻显示子任务清单 (而不是等整轮结束才知道)。
    /// </summary>
    public async Task AnnounceAsync(TaskPlan plan, CancellationToken ct = default)
    {
        if (_events is null)
            return;
        try
        {
            await _events.EmitAsync(PlanEvents.Created, CreatedPayload(plan), ct).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            AgentTelemetry.Emit("plan_event_error", "PlanRunner",
                ("event", PlanEvents.Created), ("err", Trunc(ex.Message, 160) ?? ""));
        }
    }

    /// <summary>
    /// D4 本地先行: **立刻**启动"无依赖本地节点"(输入已在手, 不必等远程产物), 与远程生成真并行。
    ///
    /// 返回 null = 本计划**没有**这种节点 —— 不许假装先行 (打点 `plan_local_first` state=skip 留痕)。
    /// 闸门关闭 (回退哑体) 时同样返回 null。
    /// </summary>
    public LocalFirstRun? StartLocalFirst(TaskPlan plan, LocalNodeContext ctx, CancellationToken ct = default)
    {
        if (!_gate())
            return null;

        var ready = plan.Nodes
            .Where(n => n.DependsOn.Count == 0 && n.RunsLocally
                        && LocalExecutorRegistry.IsWired(n.LocalExecutorId)
                        && _executors.ContainsKey(n.LocalExecutorId!))
            .ToList();

        if (ready.Count == 0)
        {
            AgentTelemetry.Emit("plan_local_first", "PlanRunner",
                ("plan_id", plan.PlanId), ("state", "skip"), ("reason", "无无依赖本地节点"));
            return null;
        }

        // 子计划复用同一执行引擎 (调度/失败/终态语义与整计划一致), 只含无依赖本地节点 ⇒ 全部 Level 0
        var sub = new TaskPlan
        {
            PlanId = plan.PlanId,
            SourceText = plan.SourceText,
            MaxParallelism = plan.MaxParallelism,
            DefaultMaxRetries = plan.DefaultMaxRetries,
        };
        sub.Nodes.AddRange(ready);

        var batch = new LocalFirstRun
        {
            NodeIds = ready.Select(n => n.Id).ToList(),
            StartedUs = Monotonic.NowUs(),
            Pending = Task.CompletedTask,
        };

        batch.Pending = Task.Run(async () =>
        {
            try
            {
                var runner = new Func<PlanNode, CancellationToken, Task<NodeExecutionResult>>(
                    (node, c) => RunNodeAsync(node, ctx, batch.Outcomes, batch.Results, c, plan.PlanId));
                await NewExecutor(runner, plan.PlanId).ExecuteAsync(sub, pollInjections: null, ct).ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                AgentTelemetry.Emit("plan_local_first_error", "PlanRunner",
                    ("plan_id", plan.PlanId), ("err", Trunc(ex.Message, 160) ?? ""));
            }
            finally
            {
                batch.MarkEnded();
            }
        }, ct);

        AgentTelemetry.Emit("plan_local_first", "PlanRunner",
            ("plan_id", plan.PlanId), ("state", "started"),
            ("nodes", ready.Count), ("ids", string.Join(",", batch.NodeIds)));

        return batch;
    }

    /// <summary>执行整张计划 (真执行体)。返回的 run.Outcomes 即前端/KPI 的唯一事实源。</summary>
    /// <param name="localFirst">D4: 已由 StartLocalFirst 跑过的无依赖本地节点 — 结果直接复用, 绝不重复执行</param>
    /// <param name="remoteWindow">D4: 远程生成窗口 (用于算"本地先行与远程生成真重叠了多少毫秒")</param>
    /// <param name="seedRun">D7b: 从检查点重建的运行态 (续跑)。非空 ⇒ 上轮已 Completed 的节点不重跑,
    /// 其产出必须已由调用方注入 <paramref name="ctx"/>.NodeOutputs —— 否则等待节点会拿到空输入。</param>
    public async Task<TaskPlanRun> RunAsync(TaskPlan plan, LocalNodeContext? ctx = null, CancellationToken ct = default,
        LocalFirstRun? localFirst = null, RemoteWindow? remoteWindow = null, TaskPlanRun? seedRun = null)
    {
        ctx ??= new LocalNodeContext();
        var enabled = _gate();
        var outcomes = new ConcurrentDictionary<string, NodeOutcome>(StringComparer.Ordinal);
        var results = new ConcurrentDictionary<string, NodeExecutionResult>(StringComparer.Ordinal);

        // D7b 续跑: 上一轮的审计行先并回台账 —— 否则收尾时 run.Outcomes 只留本轮跑过的节点,
        // 上轮 Completed 的节点从 KPI/前端事件里凭空消失 (账要连得上, 不能只看最后一段)。
        if (seedRun is not null)
            foreach (var o in seedRun.Outcomes)
                outcomes[o.NodeId] = o;

        if (localFirst is not null)
        {
            try
            {
                await localFirst.Pending.ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                AgentTelemetry.Emit("plan_local_first_error", "PlanRunner",
                    ("plan_id", plan.PlanId), ("err", Trunc(ex.Message, 160) ?? ""));
            }
            foreach (var kv in localFirst.Results)
                results[kv.Key] = kv.Value;
            foreach (var kv in localFirst.Outcomes)
                outcomes[kv.Key] = kv.Value;
        }

        Func<PlanNode, CancellationToken, Task<NodeExecutionResult>> runner = enabled
            ? (node, c) => results.TryGetValue(node.Id, out var pre)
                ? Task.FromResult(pre)
                : RunNodeAsync(node, ctx, outcomes, results, c, plan.PlanId)
            : (node, _) =>
            {
                // 哑体回退也要留审计行 (state=Skipped + 原因), 否则 run.Outcomes 空白 = 静默
                outcomes[node.Id] = DummyOutcome(node);
                return Task.FromResult(Dummy(node));
            };

        var sw = Stopwatch.StartNew();
        var executor = NewExecutor(runner, plan.PlanId);
        var run = await executor.ExecuteAsync(plan, pollInjections: null, ct, seedRun).ConfigureAwait(false);
        sw.Stop();

        // 审计与状态对齐: 只保留真正跑过的节点 (Paused/待澄清节点无产物, 不塞假数据)
        run.Outcomes = plan.Nodes
            .Where(n => outcomes.ContainsKey(n.Id))
            .Select(n => outcomes[n.Id])
            .ToList();

        var local = run.Outcomes.Count(o => o.Location is "local" or "hybrid" && o.State == PlanNodeState.Completed);
        var failed = run.Outcomes.Count(o => o.State == PlanNodeState.Failed);
        var skipped = run.Outcomes.Count(o => o.State == PlanNodeState.Skipped);
        var remoteTokens = run.Outcomes.Where(o => o.Location == "remote").Sum(o => o.Tokens);
        var localTokens = run.Outcomes.Where(o => o.Location is "local" or "hybrid").Sum(o => o.Tokens);

        // D4 重叠度量: 本地先行批次与远程生成窗口的真正交集 (不是"两次耗时相加"这种假账)
        var localFirstNodes = localFirst?.NodeIds.Count ?? 0;
        var localFirstUs = localFirst?.ElapsedUs ?? 0;
        var remoteWaitUs = remoteWindow?.WaitUs ?? 0;
        var overlapUs = 0L;
        if (localFirst is not null && remoteWindow is { } rw)
        {
            overlapUs = Math.Max(0,
                Math.Min(localFirst.EndedUs, rw.ReadyUs) - Math.Max(localFirst.StartedUs, rw.StartedUs));
        }

        // D6: 计划级 KPI 落到 run 上 —— 前端事件 / 遥测 / 对照脚本读**同一份**数字
        run.Kpi = new PlanKpi(
            Nodes: plan.Nodes.Count,
            LocalNodes: plan.Nodes.Count(n => n.Location == NodeExecutionLocation.Local),
            RemoteNodes: plan.Nodes.Count(n => n.Location == NodeExecutionLocation.Remote),
            HybridNodes: plan.Nodes.Count(n => n.Location == NodeExecutionLocation.Hybrid),
            LocalFirstNodes: localFirstNodes,
            LocalFirstMs: (int)(localFirstUs / 1000),
            OverlapMs: (int)(overlapUs / 1000),
            RemoteWaitMs: (int)(remoteWaitUs / 1000),
            LocalFirstUs: localFirstUs,
            OverlapUs: overlapUs,
            RemoteWaitUs: remoteWaitUs,
            LocalTokens: localTokens,
            WaitNodes: run.Waits.Count,
            WaitUs: run.Waits.Values.Sum(w => w.WaitUs ?? 0),
            ElapsedMs: (int)sw.ElapsedMilliseconds);

        AgentTelemetry.Emit("plan", "PlanRunner",
            ("plan_id", plan.PlanId),
            ("enabled", enabled),
            ("nodes", plan.Nodes.Count),
            ("local_ok", local),
            ("local_failed", failed),
            ("skipped", skipped),
            ("local_tokens", localTokens),
            ("remote_tokens", remoteTokens),
            ("wait_nodes", run.Waits.Count),
            ("wait_us", run.Waits.Values.Sum(w => w.WaitUs ?? 0)),
            ("local_first", localFirst is not null),
            ("local_first_nodes", localFirstNodes),
            ("local_first_ms", localFirstUs / 1000),
            ("local_first_us", localFirstUs),
            ("overlap_us", overlapUs),
            ("remote_wait_us", remoteWaitUs),
            ("elapsed_ms", sw.ElapsedMilliseconds));

        if (localFirst is not null)
        {
            AgentTelemetry.Emit("plan_local_first_overlap", "PlanRunner",
                ("plan_id", plan.PlanId),
                ("nodes", localFirstNodes),
                ("local_first_us", localFirstUs),
                ("overlap_us", overlapUs),
                ("remote_wait_us", remoteWaitUs),
                ("overlap_regime", overlapUs > 0 ? "true-overlap" : "no-overlap"));
        }

        await EmitFinishedAsync(plan, run, localFirst, overlapUs, remoteWaitUs, ct).ConfigureAwait(false);
        return run;
    }

    private async Task EmitFinishedAsync(TaskPlan plan, TaskPlanRun run, LocalFirstRun? localFirst,
        long overlapUs, long remoteWaitUs, CancellationToken ct)
    {
        if (_events is null)
            return;
        var payload = FinishedPayload(plan, run, localFirst, overlapUs, remoteWaitUs);
        try
        {
            await _events.EmitAsync(PlanEvents.Finished, payload, ct).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            AgentTelemetry.Emit("plan_event_error", "PlanRunner",
                ("event", PlanEvents.Finished), ("err", Trunc(ex.Message, 160) ?? ""));
        }
    }

    private async Task<NodeExecutionResult> RunNodeAsync(
        PlanNode node, LocalNodeContext ctx, ConcurrentDictionary<string, NodeOutcome> outcomes,
        ConcurrentDictionary<string, NodeExecutionResult> results, CancellationToken ct,
        string planId = "")
    {
        var sw = Stopwatch.StartNew();
        NodeExecutionResult result;
        try
        {
            if (node.Location == NodeExecutionLocation.Remote)
            {
                result = RemoteNode(node, ctx);
            }
            else
            {
                if (!LocalExecutorRegistry.IsWired(node.LocalExecutorId))
                {
                    result = PythonSelfTestExecutor.Fail(node.Id,
                        $"本地执行器「{node.LocalExecutorId}」未接线 (登记表 Wired=false) ⇒ 拒绝假装执行",
                        NodeFailureKind.Permanent);
                }
                else if (!_executors.TryGetValue(node.LocalExecutorId!, out var ex))
                {
                    result = PythonSelfTestExecutor.Fail(node.Id,
                        $"本地执行器「{node.LocalExecutorId}」登记与实现不一致 (登记有/实现无)", NodeFailureKind.Permanent);
                }
                else
                {
                    result = await ex.RunAsync(node, ctx, ct).ConfigureAwait(false);
                }
            }
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            result = PythonSelfTestExecutor.Fail(node.Id,
                $"本地执行器异常: {ex.GetType().Name}: {ex.Message}", NodeFailureKind.Permanent);
        }
        sw.Stop();

        if (!string.IsNullOrEmpty(result.Output))
            ctx.NodeOutputs[node.Id] = result.Output;

        var tokens = node.Location == NodeExecutionLocation.Remote ? 0L : 0L; // 本地恒 0; 远程由主链计费
        var outcome = new NodeOutcome
        {
            NodeId = node.Id,
            Location = node.LocationText,
            ExecutorId = node.LocalExecutorId,
            State = result.FinalState,
            Tokens = tokens,
            ElapsedMs = sw.ElapsedMilliseconds,
            ArtifactPath = node.RunsLocally ? ctx.ArtifactPath : null,
            Detail = Trunc(FirstNonEmpty(result.Error, result.Output), 300),
        };
        outcomes[node.Id] = outcome;
        results[node.Id] = result;

        AgentTelemetry.Emit("plan_node", "PlanRunner",
            ("plan_node", node.Id),
            ("intent", node.Intent),
            ("loc", node.LocationText),
            ("exec", node.LocalExecutorId ?? "-"),
            ("state", result.FinalState.ToString()),
            ("elapsed_ms", sw.ElapsedMilliseconds),
            ("tokens", tokens));

        await EmitNodeAsync(node, outcome, planId, ct).ConfigureAwait(false);

        return result;
    }

    /// <summary>
    /// D7 事件出口装配: 等待事件走与节点完成**同一条通道** (D5 纪律: 前端一个域看全)。
    /// 这里只做装配, 具体载荷在 <see cref="EmitWaitAsync"/>。
    /// </summary>
    private TaskPlanExecutor NewExecutor(Func<PlanNode, CancellationToken, Task<NodeExecutionResult>> runner, string planId)
        => new(runner, onWait: (node, producerId, reason, ct) => EmitWaitAsync(node, producerId, reason, planId, ct));

    /// <summary>节点进等待态 (D7): 遥测 + `plan.node` 事件, 前端立刻可见 "谁在等谁的什么"。</summary>
    private async Task EmitWaitAsync(PlanNode node, string producerId, string reason, string planId, CancellationToken ct)
    {
        var outcome = new NodeOutcome
        {
            NodeId = node.Id,
            Location = node.LocationText,
            ExecutorId = node.LocalExecutorId,
            State = PlanNodeState.Waiting,
            WaitFor = producerId,
            WaitReason = reason,
            Detail = $"等待 {producerId} 的产出 ({reason})",
        };

        AgentTelemetry.Emit("plan_wait", "PlanRunner",
            ("plan_id", planId), ("node", node.Id), ("producer", producerId), ("reason", reason));

        await EmitNodeAsync(node, outcome, planId, ct).ConfigureAwait(false);
    }

    /// <summary>单节点事件 (D5) —— 前端按节点看"哪步在哪跑、跑了多久、成没成"</summary>
    private async Task EmitNodeAsync(PlanNode node, NodeOutcome outcome, string planId, CancellationToken ct)
    {
        if (_events is null)
            return;
        try
        {
            await _events.EmitAsync(PlanEvents.Node, NodePayload(node, outcome, planId), ct).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            AgentTelemetry.Emit("plan_event_error", "PlanRunner",
                ("event", PlanEvents.Node), ("err", Trunc(ex.Message, 160) ?? ""));
        }
    }

    // ---- D5 事件载荷 (手写 JSON: 零反射, AOT 安全; 只暴露前端需要的字段) ----

    private static string CreatedPayload(TaskPlan plan)
    {
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteString("plan_id", plan.PlanId);
            w.WriteNumber("nodes_total", plan.Nodes.Count);
            w.WriteNumber("local", plan.Nodes.Count(n => n.Location == NodeExecutionLocation.Local));
            w.WriteNumber("hybrid", plan.Nodes.Count(n => n.Location == NodeExecutionLocation.Hybrid));
            w.WriteNumber("remote", plan.Nodes.Count(n => n.Location == NodeExecutionLocation.Remote));
            w.WriteStartArray("nodes");
            foreach (var n in plan.Nodes)
            {
                w.WriteStartObject();
                w.WriteString("id", n.Id);
                w.WriteString("text", Trunc(n.Text, 160) ?? "");
                w.WriteString("intent", n.Intent);
                w.WriteString("location", n.LocationText);
                w.WriteString("executor", n.LocalExecutorId ?? "");
                w.WriteNumber("level", n.Level);
                w.WriteBoolean("depends_on_parent", n.DependsOn.Count > 0);
                w.WriteStartArray("depends_on");
                foreach (var d in n.DependsOn)
                    w.WriteStringValue(d);
                w.WriteEndArray();
                w.WriteEndObject();
            }
            w.WriteEndArray();
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    private static string NodePayload(PlanNode node, NodeOutcome outcome, string planId)
    {
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteString("plan_id", planId);
            w.WriteString("node_id", outcome.NodeId);
            w.WriteString("intent", node.Intent);
            w.WriteString("location", outcome.Location);
            w.WriteString("executor", outcome.ExecutorId ?? "");
            w.WriteString("state", outcome.State.ToString());
            w.WriteNumber("elapsed_ms", outcome.ElapsedMs);
            w.WriteNumber("tokens", outcome.Tokens);
            w.WriteString("artifact", outcome.ArtifactPath ?? "");
            // D7: 等待中的节点前端必须能直接看到"在等谁、为什么" (不是一个孤零零的 waiting)
            w.WriteString("wait_for", outcome.WaitFor ?? "");
            w.WriteString("wait_reason", outcome.WaitReason ?? "");
            w.WriteString("detail", Trunc(outcome.Detail, 300) ?? "");
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    private static string FinishedPayload(TaskPlan plan, TaskPlanRun run, LocalFirstRun? localFirst,
        long overlapUs, long remoteWaitUs)
    {
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteString("plan_id", plan.PlanId);
            w.WriteString("run_id", run.RunId);
            w.WriteString("state", run.State.ToString());
            w.WriteNumber("nodes_total", plan.Nodes.Count);
            w.WriteNumber("local_ok", run.Outcomes.Count(o => o.Location is "local" or "hybrid" && o.State == PlanNodeState.Completed));
            w.WriteNumber("failed", run.Outcomes.Count(o => o.State == PlanNodeState.Failed));
            w.WriteNumber("skipped", run.Outcomes.Count(o => o.State == PlanNodeState.Skipped));
            w.WriteNumber("local_tokens", run.Outcomes.Where(o => o.Location is "local" or "hybrid").Sum(o => o.Tokens));
            w.WriteNumber("remote_tokens", run.Outcomes.Where(o => o.Location == "remote").Sum(o => o.Tokens));
            w.WriteBoolean("local_first", localFirst is not null);
            w.WriteNumber("local_first_nodes", localFirst?.NodeIds.Count ?? 0);
            w.WriteNumber("local_first_ms", localFirst?.ElapsedMs ?? 0);
            w.WriteNumber("local_first_us", localFirst?.ElapsedUs ?? 0);
            w.WriteNumber("overlap_ms", overlapUs / 1000);
            w.WriteNumber("overlap_us", overlapUs);
            w.WriteNumber("remote_wait_ms", remoteWaitUs / 1000);
            w.WriteNumber("remote_wait_us", remoteWaitUs);
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    /// <summary>远程节点: 主链已生成, 这里只登记, **绝不二次调用模型**</summary>
    private static NodeExecutionResult RemoteNode(PlanNode node, LocalNodeContext ctx)
    {
        if (!ctx.HasRemoteProduct)
        {
            return new NodeExecutionResult
            {
                NodeId = node.Id,
                FinalState = PlanNodeState.Skipped,
                Output = null,
                Error = "远程产物未就绪 (主链尚未生成) ⇒ 只登记不执行",
                FailureKind = NodeFailureKind.Transient,
            };
        }
        return new NodeExecutionResult
        {
            NodeId = node.Id,
            FinalState = PlanNodeState.Completed,
            Output = ctx.RemoteText,
        };
    }

    /// <summary>回退哑体 (仅闸门关闭时; 打点暴露"哑体在用")</summary>
    private static NodeExecutionResult Dummy(PlanNode node)
    {
        AgentTelemetry.Emit(DummyRunnerPoint, "PlanRunner", ("plan_node", node.Id), ("loc", node.LocationText));
        return new NodeExecutionResult
        {
            NodeId = node.Id,
            FinalState = PlanNodeState.Skipped,
            Output = null,
        };
    }

    /// <summary>哑体审计行 (闸门关闭): 位置/执行器照记, 状态 Skipped + 原因 —— 同题对照时可直接与真执行体 diff</summary>
    private static NodeOutcome DummyOutcome(PlanNode node) => new()
    {
        NodeId = node.Id,
        Location = node.LocationText,
        ExecutorId = node.LocalExecutorId,
        State = PlanNodeState.Skipped,
        Tokens = 0,
        ElapsedMs = 0,
        Detail = $"哑体回退 ({EnableEnvName}=0): 只演练调度语义, 不真执行本地节点",
    };

    private static string? FirstNonEmpty(params string?[] xs)
    {
        foreach (var x in xs)
        {
            if (!string.IsNullOrWhiteSpace(x))
                return x;
        }
        return null;
    }

    private static string? Trunc(string? s, int n) =>
        string.IsNullOrEmpty(s) ? s : (s.Length <= n ? s : s[..n] + "…");
}
