using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
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

        /// <summary>
        /// 工作区根 (R516 节点产物契约): 非空 = 编排器**自己**持有逐节点快照差 (本地/远端节点统一),
        /// 并据此做范围机检与「声明了范围却零产物」的假绿防护。null = 关闭 (向后兼容, 旧行为)。
        /// </summary>
        public string? WorkspaceRoot { get; init; }

        /// <summary>节点写范围契约 (nodeId → 路径声明); null/空 = 未声明 ⇒ 不做越界机检。</summary>
        public IReadOnlyDictionary<string, IReadOnlyList<string>>? NodeScopes { get; init; }

        /// <summary>声明了写范围的节点必须产出 ≥1 个范围内文件 (否则节点 Failed) —— 修 R515 的 5 ms 假绿。</summary>
        public bool RequireScopedArtifacts { get; init; } = true;

        /// <summary>
        /// R518 节点预算自适应: 远端节点因「零产物」(假绿防护) 被判 Failed 时, 同节点**升预算重试**的次数上限。
        /// 0 = 关闭 (旧行为, 向后兼容); 1 = 允许一次 2 倍升预算 (单节点预算上界仍为 32 = 动作环硬顶)。
        /// 只对「零产物」这一种失败升预算 —— 越界写 / 异常 / 本地节点一律不重试 (不掩盖真失败)。
        /// </summary>
        public int MaxBudgetEscalations { get; init; }
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

        /// <summary>本节点落盘产物 (快照差; 空 = 未观察到写盘 ⇒ 声明了范围的节点会被判 Failed)。</summary>
        public IReadOnlyList<string> Artifacts { get; init; } = Array.Empty<string>();

        /// <summary>本节点的写范围声明 (空 = 未声明; 报告须如实标注「未声明」, 不得默认合规)。</summary>
        public IReadOnlyList<string> Scope { get; init; } = Array.Empty<string>();

        /// <summary>R518 本节点**实际**用的动作步数预算 (含升预算重试后的值; 未重试 = 编排选项的 NodeMaxSteps)。</summary>
        public int BudgetSteps { get; init; }

        /// <summary>R518 本节点升预算重试次数 (0 = 一次过)。</summary>
        public int Escalations { get; init; }

        /// <summary>R518 逐次尝试留痕 (`步数:终态`, 如 `6:Failed 12:Completed`) —— 重试不许静默。</summary>
        public IReadOnlyList<string> Attempts { get; init; } = Array.Empty<string>();
    }

    /// <summary>范围机检违规记录 (越界写 / 声明范围却零产物)。</summary>
    public sealed record ScopeViolation(string NodeId, string Path, string Kind);

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
    private readonly Dictionary<string, IReadOnlyList<string>> _artifacts = new(StringComparer.Ordinal);
    private readonly List<ScopeViolation> _violations = new();
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
        if (Opt.NodeMaxSteps > MaxNodeBudget) throw new ArgumentOutOfRangeException(nameof(options), $"NodeMaxSteps 上限 {MaxNodeBudget} (与动作环硬顶一致)");
        if (Opt.MaxBudgetEscalations < 0 || Opt.MaxBudgetEscalations > 3)
            throw new ArgumentOutOfRangeException(nameof(options), "MaxBudgetEscalations 越界 0..3 (升预算重试不许无界)");
    }

    /// <summary>单节点动作步数硬顶 (与动作环一致; 升预算重试也不许越过)。</summary>
    public const int MaxNodeBudget = 32;

    public Options Opt { get; }

    /// <summary>本次运行的全部节点遥测 (按完成先后)。</summary>
    public IReadOnlyList<NodeTelemetry> Telemetry => _telemetry;

    /// <summary>逐节点落盘产物 (相对工作区路径, 前缀 `A `/`M `/`D ` = 增/改/删; WorkspaceRoot 为空时恒为空)。</summary>
    public IReadOnlyDictionary<string, IReadOnlyList<string>> NodeArtifacts => _artifacts;

    /// <summary>范围机检违规 (越界写 / 声明范围却零产物); 非空 ⇒ 相关节点已判 Failed。</summary>
    public IReadOnlyList<ScopeViolation> ScopeViolations => _violations;

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

    /// <summary>本次运行的模型外调用总步数上界 (节点数 × 单节点预算; 未含升预算重试)。</summary>
    public int BudgetCeiling => _telemetry.Count(t => !t.IsLocal) * Opt.NodeMaxSteps;

    /// <summary>R518 含升预算重试的**实际**预算上界 (Σ 逐节点本次实际预算; 与 BudgetCeiling 分列, 禁混算)。</summary>
    public int BudgetCeilingEffective => _telemetry.Where(t => !t.IsLocal).Sum(t => t.BudgetSteps > 0 ? t.BudgetSteps : Opt.NodeMaxSteps);

    /// <summary>R518 升预算重试总次数 (0 = 本运行无重试)。</summary>
    public int EscalationCount => _telemetry.Sum(t => t.Escalations);

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
        _artifacts.Clear();
        _violations.Clear();

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
        var scope = ScopeOf(node.Id);
        var root = Opt.WorkspaceRoot;
        var before = root is null ? null : Snapshot(root);
        await EmitAsync("plan.node", node, "Running", 0, 0, "", ct).ConfigureAwait(false);

        var executorId = node.LocalExecutorId ?? "";
        var budget = Opt.NodeMaxSteps;
        var escalations = 0;
        var attempts = new List<string>();
        IReadOnlyList<string> changed = Array.Empty<string>();
        NodeExecutionResult result;

        // ── 一次真实执行尝试 (步数 = 本次预算) ──
        async Task<NodeExecutionResult> AttemptAsync(int steps)
        {
            NodeExecutionResult r;
            var execId = node.LocalExecutorId ?? "";
            try
            {
                if (isLocal)
                {
                    var exec = FindLocalExecutor(node.LocalExecutorId);
                    if (exec is null)
                    {
                        r = Fail(node.Id, $"本地执行器缺失: {node.LocalExecutorId ?? "(null)"}");
                    }
                    else
                    {
                        var ctx = Opt.LocalContextFactory?.Invoke(node) ?? new LocalNodeContext { SessionId = _sessionId };
                        foreach (var pair in upstream) ctx.NodeOutputs[pair.Key] = pair.Value;
                        r = await exec.RunAsync(node, ctx, ct).ConfigureAwait(false);
                        execId = exec.Id;
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
                    r = await remote(node, deps, steps, ct).ConfigureAwait(false);
                }
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested)
            {
                throw;
            }
            catch (Exception ex)
            {
                r = Fail(node.Id, $"节点执行抛异常: {ex.GetType().Name}");
            }
            if (execId.Length > 0) executorId = execId;
            return r;
        }

        // ── R518 节点预算自适应: 「声明了范围却零产物」的节点 ⇒ 升预算重试 (上界 32; 其余失败不重试) ──
        while (true)
        {
            result = await AttemptAsync(budget).ConfigureAwait(false);

            changed = Array.Empty<string>();
            if (root is not null)
            {
                changed = Diff(before!, Snapshot(root));
                lock (gate) _artifacts[node.Id] = changed;
                result = EnforceScope(node, result, scope, changed);
            }
            attempts.Add($"{budget}:{result.FinalState}");

            if (isLocal || result.FinalState != PlanNodeState.Failed) break;
            if (escalations >= Opt.MaxBudgetEscalations || budget >= MaxNodeBudget) break;
            if (!_violations.Any(v => v.NodeId == node.Id && v.Kind == "no_artifact")) break;

            // 重试前撤销本次「零产物」记账 (重试会重新记账, 避免同因重复计数)
            _violations.RemoveAll(v => v.NodeId == node.Id && v.Kind == "no_artifact");
            var prevBudget = budget;
            escalations++;
            budget = Math.Min(MaxNodeBudget, budget * 2);
            await EmitAsync("plan.node", node, "Retry", budget, (Monotonic.NowUs() - started) / 1000,
                $"零产物 (假绿防护) ⇒ 升预算重试: 步数 {prevBudget}→{budget}", ct)
                .ConfigureAwait(false);
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
            result.Error ?? string.Empty)
        {
            Artifacts = changed,
            Scope = scope ?? Array.Empty<string>(),
            BudgetSteps = budget,
            Escalations = escalations,
            Attempts = attempts,
        });

        await EmitAsync("plan.node", node, result.FinalState.ToString(),
            isLocal ? 0 : budget, (ended - started) / 1000, result.Error ?? "", ct).ConfigureAwait(false);

        return result;
    }

    /// <summary>
    /// R516 范围机检 (起臂前, 零 LLM 成本): 未知节点 + **同层写范围重叠** ⇒ 拒收。
    /// 静态门面, 与 <see cref="NodeScopeFile.Validate"/> 同源 (单一权威实现)。
    /// </summary>
    public static List<string> ValidateScopes(TaskPlan plan, IReadOnlyDictionary<string, IReadOnlyList<string>>? scopes)
        => NodeScopeFile.Validate(plan, scopes);

    private IReadOnlyList<string>? ScopeOf(string nodeId)
        => Opt.NodeScopes is not null && Opt.NodeScopes.TryGetValue(nodeId, out var s) && s.Count > 0 ? s : null;

    /// <summary>
    /// 节点成功判据**绑产物证据** (R516):
    ///   ① 越界写 (不在声明范围内) ⇒ 节点 Failed + 记录违规 (不静默、不回落成「Completed」);
    ///   ② 声明了范围却**零产物** ⇒ 节点 Failed (假绿防护; R515 真机 n3 5 ms/0 产物仍记 Completed 就是这个洞)。
    /// 未声明范围的节点不受 ② 约束 (向后兼容), 但其产物仍记账 (报告如实标注「未声明」)。
    /// </summary>
    private NodeExecutionResult EnforceScope(PlanNode node, NodeExecutionResult result, IReadOnlyList<string>? scope, IReadOnlyList<string> changed)
    {
        if (scope is null || result.FinalState != PlanNodeState.Completed) return result;

        var outside = new List<string>();
        foreach (var entry in changed)
        {
            if (entry.Length <= 2) continue;
            var rel = entry[2..];
            if (!NodeScopeFile.InScope(scope, rel)) outside.Add(rel);
        }
        if (outside.Count > 0)
        {
            foreach (var rel in outside) _violations.Add(new ScopeViolation(node.Id, rel, "out_of_scope"));
            return Fail(node.Id, "越界写入 (fail-closed): " + string.Join(", ", outside) + $" (声明范围: {string.Join(",", scope)})");
        }

        if (Opt.RequireScopedArtifacts)
        {
            var inScopeArtifact = changed.Any(e => e.Length > 2 && (e[0] == 'A' || e[0] == 'M') && NodeScopeFile.InScope(scope, e[2..]));
            if (!inScopeArtifact)
            {
                _violations.Add(new ScopeViolation(node.Id, "", "no_artifact"));
                return Fail(node.Id, "节点无产物 (假绿防护): 声明了写范围但未产出任何范围内文件");
            }
        }
        return result;
    }

    private sealed record FileStamp(long Length, long Ticks);

    /// <summary>
    /// R518 节点产物判定: 语言运行时的**编译缓存**不是节点产物 (Python `__pycache__/*.pyc` 等)。
    /// 起因 (R518 真机自抓): 节点按题面「写自测并运行」⇒ 解释器自动落 `__pycache__/*.pyc`,
    /// 被 diff 判为越界写入 ⇒ 整链 fail-closed, 节点真实产物 cli.py 都还没写就被判死。
    /// 口径: 只排除运行期自动生成的字节码缓存; 源码/数据文件一律照旧纳入范围契约 (负控见单测)。
    /// </summary>
    private static bool IsRuntimeCache(string rel)
    {
        var parts = rel.Split('/');
        for (var i = 0; i < parts.Length; i++)
            if (parts[i] is "__pycache__" or ".pytest_cache" or ".mypy_cache" or ".ruff_cache") return true;
        var name = parts[parts.Length - 1];
        return name.EndsWith(".pyc", StringComparison.OrdinalIgnoreCase)
            || name.EndsWith(".pyo", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>工作区快照 (跳过编排器自身的产物目录 `.orchestrator` 与运行期缓存)。</summary>
    private static Dictionary<string, FileStamp> Snapshot(string root)
    {
        var map = new Dictionary<string, FileStamp>(StringComparer.Ordinal);
        try
        {
            foreach (var path in Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories))
            {
                var rel = Path.GetRelativePath(root, path);
                if (rel.StartsWith(".orchestrator", StringComparison.Ordinal)) continue;
                var norm = rel.Replace('\\', '/');
                if (IsRuntimeCache(norm)) continue;
                try
                {
                    var fi = new FileInfo(path);
                    map[norm] = new FileStamp(fi.Length, fi.LastWriteTimeUtc.Ticks);
                }
                catch (IOException) { }
            }
        }
        catch (IOException)
        {
            // 快照失败 ⇒ 返回已收集部分 (不掩盖节点结论); 记为半快照而非静默成功
        }
        return map;
    }

    private static List<string> Diff(Dictionary<string, FileStamp> before, Dictionary<string, FileStamp> after)
    {
        var changed = new List<string>();
        foreach (var pair in after)
        {
            if (!before.TryGetValue(pair.Key, out var old)) changed.Add("A " + pair.Key);
            else if (old.Length != pair.Value.Length || old.Ticks != pair.Value.Ticks) changed.Add("M " + pair.Key);
        }
        foreach (var pair in before)
            if (!after.ContainsKey(pair.Key)) changed.Add("D " + pair.Key);
        changed.Sort(StringComparer.Ordinal);
        return changed;
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
