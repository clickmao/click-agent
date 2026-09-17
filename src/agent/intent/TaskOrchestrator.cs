using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.registry;

namespace agent.intent;

/// <summary>
/// 长任务编排器 (R515) —— 让「一个长项目」变成「多次真实执行」。
///
/// 与既有件的关系:
///   * <see cref="TaskPlanExecutor"/> = 调度引擎 (依赖序 / 同层并发 / 运行时等待 / 重试 / 检查点) —— 复用不改;
///   * <see cref="PlanRunner"/> = 主链产物登记 + 「本地先行」重叠窗口测量 —— 复用其单调钟口径 (<see cref="Monotonic"/>);
///   * 本类 = **节点 = 一次真实执行单元** 的驱动层: 远端节点由宿主注入真实 agent 轮次
///     (每节点独立步数预算 ⇒ 总动作步数 = Σ 节点预算, 不再受单次动作环硬顶 32 封顶),
///     本地节点走零 LLM 子进程执行器, 同层「本地 + 远端」并发执行 (子任务同步进行), 逐节点墙钟遥测。
///
/// 诚实边界: 本类**不产生任务分解** —— 节点来自计划来源 (规则细分 / 计划文件 TaskPlanFile)。
/// 分解质量归计划来源; 本类只保证「逐节点真执行 + 预算按节点计 + 重叠可测 + 失败不静默」。
/// </summary>
public sealed class TaskOrchestrator
{
    /// <summary>编排选项。</summary>
    public sealed record Options
    {
        /// <summary>单节点动作步数预算 (每节点独立; 与动作环上限一致 = 1..32)。</summary>
        public int NodeMaxSteps { get; init; } = 6;

        /// <summary>节点数上限 (fail-closed: 超出直接拒绝, 不静默截断)。</summary>
        public int MaxNodes { get; init; } = 24;

        /// <summary>本地节点与同层远端节点并发 (子任务同步进行)。</summary>
        public bool ConcurrentLocalFirst { get; init; } = true;

        /// <summary>本地节点上下文工厂 (宿主注入: 产物路径 / python 路径 / 运行闸); null = 默认上下文。</summary>
        public Func<PlanNode, LocalNodeContext>? LocalContextFactory { get; init; }
    }

    /// <summary>节点墙钟遥测 (微秒单调钟; 本地/远端重叠窗口由此计算)。</summary>
    public sealed record NodeTelemetry(
        string NodeId,
        string Location,
        string Executor,
        string State,
        int Level,
        long StartedUs,
        long EndedUs,
        int OutputChars,
        string Error)
    {
        /// <summary>本节点墙钟耗时 (ms)。</summary>
        public long ElapsedMs => Math.Max(0, (EndedUs - StartedUs) / 1000);

        /// <summary>是否本地执行 (零 token 通道)。</summary>
        public bool IsLocal => Location is "local" or "hybrid";
    }

    /// <summary>远端节点执行体 (宿主注入): 一次真实 agent 轮次, 预算 = nodeMaxSteps。</summary>
    /// <param name="node">当前节点 (Text/Id/Level/依赖)。</param>
    /// <param name="upstream">已完成上游节点产出 (仅本节点依赖的; 键 = 节点 Id)。</param>
    /// <param name="nodeMaxSteps">本节点动作步数预算 (由编排选项给出)。</param>
    /// <param name="ct">取消标记。</param>
    public delegate Task<NodeExecutionResult> RemoteNodeRunner(
        PlanNode node,
        IReadOnlyDictionary<string, string> upstream,
        int nodeMaxSteps,
        CancellationToken ct);

    private readonly ILocalNodeExecutor[] _local;
    private readonly IPlanEventSink? _events;
    private readonly agent.recovery.CheckpointStore? _store;
    private readonly string _sessionId;
    private readonly List<NodeTelemetry> _telemetry = new();
    private string _planId = string.Empty;

    public TaskOrchestrator(
        IEnumerable<ILocalNodeExecutor>? localExecutors = null,
        IPlanEventSink? events = null,
        agent.recovery.CheckpointStore? checkpointStore = null,
        string sessionId = "",
        Options? options = null)
    {
        _local = (localExecutors ?? Array.Empty<ILocalNodeExecutor>()).ToArray();
        _events = events;
        _store = checkpointStore;
        _sessionId = sessionId;
        Opt = options ?? new Options();
        if (Opt.NodeMaxSteps < 1) throw new ArgumentOutOfRangeException(nameof(options), "NodeMaxSteps 必须 ≥ 1");
        if (Opt.NodeMaxSteps > 32) throw new ArgumentOutOfRangeException(nameof(options), "NodeMaxSteps 上限 32 (与动作环硬顶一致)");
    }

    public Options Opt { get; }

    /// <summary>本次运行的全部节点遥测 (按完成先后)。</summary>
    public IReadOnlyList<NodeTelemetry> Telemetry => _telemetry;

    /// <summary>本地节点与远端节点的墙钟重叠 (ms): 逐对求交后取并集上界 (可测的「同步进行」证据)。</summary>
    public long OverlapMs
    {
        get
        {
            var locals = _telemetry.Where(t => t.IsLocal).ToArray();
            var remotes = _telemetry.Where(t => !t.IsLocal).ToArray();
            long total = 0;
            foreach (var l in locals)
            {
                long best = 0;
                foreach (var r in remotes)
                {
                    long lo = Math.Max(l.StartedUs, r.StartedUs);
                    long hi = Math.Min(l.EndedUs, r.EndedUs);
                    if (hi > lo) best = Math.Max(best, (hi - lo) / 1000);
                }
                total += best;
            }
            return total;
        }
    }

    /// <summary>本次运行的模型外调用总步数上界 (节点数 × 单节点预算)。</summary>
    public int BudgetCeiling => _telemetry.Count(t => !t.IsLocal) * Opt.NodeMaxSteps;

    /// <summary>
    /// 驱动整个计划: 逐节点真执行, 依赖序 + 同层并发, 每节点独立预算, 逐节点落检查点与事件。
    /// 返回调度引擎的终态运行记录 (含每节点终态)。
    /// </summary>
    public async Task<TaskPlanRun> RunAsync(
        TaskPlan plan,
        RemoteNodeRunner remote,
        Func<InjectedInstruction?>? pollInjections = null,
        CancellationToken ct = default,
        TaskPlanRun? seedRun = null)
    {
        if (plan is null) throw new ArgumentNullException(nameof(plan));
        if (remote is null) throw new ArgumentNullException(nameof(remote));
        if (plan.Nodes.Count == 0) throw new ArgumentException("计划为空: 无节点可执行", nameof(plan));
        if (plan.Nodes.Count > Opt.MaxNodes)
            throw new ArgumentException($"节点数 {plan.Nodes.Count} 超上限 {Opt.MaxNodes} (fail-closed, 不静默截断)", nameof(plan));

        _planId = plan.PlanId;
        _telemetry.Clear();

        if (Opt.ConcurrentLocalFirst) plan.MaxParallelism = Math.Max(2, plan.MaxParallelism);

        var upstream = new Dictionary<string, string>(StringComparer.Ordinal);
        var gate = new object();

        Task<NodeExecutionResult> Runner(PlanNode node, CancellationToken nodeCt)
            => RunNodeAsync(node, remote, upstream, gate, nodeCt);

        var executor = new TaskPlanExecutor(Runner, null, null, null, _store, _sessionId);
        var run = await executor.ExecuteAsync(plan, pollInjections, ct, seedRun).ConfigureAwait(false);
        return run;
    }

    private async Task<NodeExecutionResult> RunNodeAsync(
        PlanNode node,
        RemoteNodeRunner remote,
        Dictionary<string, string> upstream,
        object gate,
        CancellationToken ct)
    {
        var started = Monotonic.NowUs();
        var isLocal = node.RunsLocally;
        await EmitAsync("plan.node", node, "Running", 0, 0, "", ct).ConfigureAwait(false);

        NodeExecutionResult result;
        var executorId = node.LocalExecutorId ?? "";
        try
        {
            if (isLocal)
            {
                var exec = FindLocalExecutor(node.LocalExecutorId);
                if (exec is null)
                {
                    result = Fail(node.Id, $"本地执行器缺失: {node.LocalExecutorId ?? "(null)"}");
                }
                else
                {
                    var ctx = Opt.LocalContextFactory?.Invoke(node) ?? new LocalNodeContext { SessionId = _sessionId };
                    foreach (var pair in upstream) ctx.NodeOutputs[pair.Key] = pair.Value;
                    result = await exec.RunAsync(node, ctx, ct).ConfigureAwait(false);
                    executorId = exec.Id;
                }
            }
            else
            {
                Dictionary<string, string> deps;
                lock (gate)
                {
                    deps = new Dictionary<string, string>(StringComparer.Ordinal);
                    foreach (var dep in node.DependsOn)
                        if (upstream.TryGetValue(dep, out var text)) deps[dep] = text;
                }
                result = await remote(node, deps, Opt.NodeMaxSteps, ct).ConfigureAwait(false);
            }
        }
        catch (OperationCanceledException) when (ct.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            result = Fail(node.Id, $"节点执行抛异常: {ex.GetType().Name}");
        }

        var ended = Monotonic.NowUs();
        var output = result.Output ?? string.Empty;
        lock (gate)
        {
            if (result.FinalState == PlanNodeState.Completed && output.Length > 0) upstream[node.Id] = output;
        }

        _telemetry.Add(new NodeTelemetry(
            node.Id,
            node.LocationText,
            isLocal ? executorId : "agent-turn",
            result.FinalState.ToString(),
            node.Level,
            started,
            ended,
            output.Length,
            result.Error ?? string.Empty));

        await EmitAsync("plan.node", node, result.FinalState.ToString(),
            isLocal ? 0 : Opt.NodeMaxSteps, (ended - started) / 1000, result.Error ?? "", ct).ConfigureAwait(false);

        return result;
    }

    private ILocalNodeExecutor? FindLocalExecutor(string? id)
    {
        if (string.IsNullOrEmpty(id)) return null;
        foreach (var e in _local)
            if (string.Equals(e.Id, id, StringComparison.OrdinalIgnoreCase)) return e;
        return null;
    }

    private static NodeExecutionResult Fail(string nodeId, string error)
        => new()
        {
            NodeId = nodeId,
            FinalState = PlanNodeState.Failed,
            Error = error,
            FailureKind = NodeFailureKind.Permanent,
        };

    private async Task EmitAsync(string ev, PlanNode node, string state, int steps, long elapsedMs, string detail, CancellationToken ct)
    {
        if (_events is null) return;
        var json = new StringBuilder(200)
            .Append("{\"plan_id\":\"").Append(Escape(_planId))
            .Append("\",\"node_id\":\"").Append(Escape(node.Id))
            .Append("\",\"state\":\"").Append(Escape(state))
            .Append("\",\"level\":").Append(node.Level.ToString(CultureInfo.InvariantCulture))
            .Append(",\"location\":\"").Append(Escape(node.LocationText))
            .Append("\",\"steps\":").Append(steps.ToString(CultureInfo.InvariantCulture))
            .Append(",\"elapsed_ms\":").Append(elapsedMs.ToString(CultureInfo.InvariantCulture))
            .Append(",\"detail\":\"").Append(Escape(detail))
            .Append("\"}").ToString();
        try
        {
            await _events.EmitAsync(ev, json, ct).ConfigureAwait(false);
        }
        catch
        {
            // 纪律 (与 PlanRunner D5 一致): 事件出口异常不得打断计划。
        }
    }

    /// <summary>零反射 JSON 转义 (AOT: 禁 STJ 反射序列化路径)。</summary>
    private static string Escape(string? s)
    {
        if (string.IsNullOrEmpty(s)) return string.Empty;
        var sb = new StringBuilder(s.Length + 8);
        foreach (var c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                    else sb.Append(c);
                    break;
            }
        }
        return sb.ToString();
    }
}
