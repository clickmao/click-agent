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
/// 本地节点执行上下文 (v0.22.0 exp9 D3) —— 本地执行器只允许依赖这些**本地事实**,
/// 禁止联网/调模型 (接口契约: 本地执行 = 零 token)。
/// </summary>
public sealed class LocalNodeContext
{
    /// <summary>本轮产物路径 (远程节点产出的可跑对象; 由台账/主链提供)</summary>
    public string? ArtifactPath { get; set; }

    /// <summary>本轮远程生成正文 (Hybrid 节点的第二段输入; 主链产出, 不重复调用模型)</summary>
    public string? RemoteText { get; set; }

    /// <summary>远程产物是否已就绪 (未就绪 ⇒ 依赖它的本地节点不许假装成功)</summary>
    public bool HasRemoteProduct => !string.IsNullOrEmpty(ArtifactPath) || !string.IsNullOrEmpty(RemoteText);

    public string? SessionId { get; init; }

    /// <summary>本轮用户原文 (v0.22.0 exp9 D4): 无依赖本地文本节点的输入 —— 模型生成前即已就绪,
    /// 这正是"本地先行"能真并行的前提。</summary>
    public string? SourceText { get; init; }

    /// <summary>python 解释器路径 (null = 由运行级解析器决定)</summary>
    public string? PythonPath { get; init; }

    public int TimeoutMs { get; init; } = PythonRunVerifier.DefaultTimeoutMs;

    /// <summary>运行级闸门 (null = 读 AGENTFRAMEWORK_PY_RUN)</summary>
    public Func<bool>? PythonRunGate { get; init; }

    /// <summary>上游节点输出 (键=节点 Id; 由 PlanRunner 按执行序写入, 本地执行器可读)</summary>
    public Dictionary<string, string?> NodeOutputs { get; } = new(StringComparer.Ordinal);
}

/// <summary>
/// 本地节点执行器 (v0.22.0 exp9 D3)。实现方契约:
///   ① 零 LLM 调用、零网络; ② 跨平台零 shell (ProcessStartInfo.ArgumentList / 纯内存计算);
///   ③ 失败必须给真实原因 (禁静默返回成功 —— "哑体"退化的反面判据)。
/// </summary>
public interface ILocalNodeExecutor
{
    /// <summary>登记 Id (与 LocalExecutorRegistry 一致)</summary>
    string Id { get; }

    Task<NodeExecutionResult> RunAsync(PlanNode node, LocalNodeContext ctx, CancellationToken ct);
}

/// <summary>
/// 本地跑产物自带的无头自测 (v0.22.0 exp9 D3): `python3 &lt;artifact&gt; --selftest`, 退出码即判据。
/// 复用 L5 的 PythonRunVerifier (进程级证据: 退出码/耗时/stderr), 不新造执行通道。
/// 诚实边界: 只判"产物自己的 --selftest 通过"; 逻辑正确性需真机回放 (未接线, 见 D3b)。
/// </summary>
public sealed class PythonSelfTestExecutor : ILocalNodeExecutor
{
    public string Id => LocalExecutorRegistry.PythonSelfTest;

    public async Task<NodeExecutionResult> RunAsync(PlanNode node, LocalNodeContext ctx, CancellationToken ct)
    {
        var path = ctx.ArtifactPath;
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
            return Fail(node.Id, "无本地可跑对象: 产物未落盘 (远程节点未产出)", NodeFailureKind.Permanent);

        string content;
        try
        {
            content = await File.ReadAllTextAsync(path, ct).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return Fail(node.Id, $"读取产物失败: {ex.GetType().Name}: {ex.Message}", NodeFailureKind.Permanent);
        }

        if (!ArtifactCheck.MentionsSelfTest(content))
            return Fail(node.Id, "产物缺 --selftest 无头入口 (静态前缀契约: SessionBaseline.cs:53) ⇒ 本地无判据可跑",
                NodeFailureKind.Permanent);

        var gate = ctx.PythonRunGate ?? (() => PythonRunVerifier.IsEnabled());
        if (!gate())
        {
            // 环境闸门关闭: 诚实登记为 Skipped (不是成功, 也不是失败) —— D6 KPI 靠这条发现"本地能力被环境挡住"
            AgentTelemetry.Emit("plan_local_gated", "PlanRunner",
                ("node", node.Id), ("exec", Id), ("env", PythonRunVerifier.EnableEnvName));
            return new NodeExecutionResult
            {
                NodeId = node.Id,
                FinalState = PlanNodeState.Skipped,
                Output = null,
                Error = $"运行级验证未开启 ({PythonRunVerifier.EnableEnvName}≠1) ⇒ 本轮只登记不真跑",
                FailureKind = NodeFailureKind.Permanent,
            };
        }

        var run = await PythonRunVerifier
            .RunAsync(path, ctx.PythonPath, workingDir: null, args: ["--selftest"],
                timeoutMs: ctx.TimeoutMs, explicitlyEnabled: true, ct: ct)
            .ConfigureAwait(false);

        if (!run.Ran)
            return Fail(node.Id, $"本地未跑起来: {run.Detail}", NodeFailureKind.Transient);

        var tail = Tail(run.StdOut, 400);
        if (run.TimedOut)
            return Fail(node.Id, $"自测超时 ({run.ElapsedMs}ms): {tail}", NodeFailureKind.Transient);

        if (run.ExitCode == 0)
        {
            return new NodeExecutionResult
            {
                NodeId = node.Id,
                FinalState = PlanNodeState.Completed,
                Output = $"exit=0 ({run.ElapsedMs}ms)\n{tail}",
            };
        }

        return Fail(node.Id, $"自测失败 exit={run.ExitCode} ({run.ElapsedMs}ms): {tail}{Err(run.StdErr)}",
            NodeFailureKind.Transient);
    }

    internal static NodeExecutionResult Fail(string nodeId, string detail, NodeFailureKind kind) =>
        new() { NodeId = nodeId, FinalState = PlanNodeState.Failed, Error = detail, FailureKind = kind };

    private static string Err(string stderr) => string.IsNullOrWhiteSpace(stderr) ? "" : $"\n[stderr] {Tail(stderr, 200)}";

    internal static string Tail(string s, int n) => string.IsNullOrEmpty(s) ? "" : (s.Length <= n ? s : s[^n..]);
}

/// <summary>
/// 本地文本处理 / 证据汇总 (v0.22.0 exp9 D3): 统计/摘要/格式化 —— 纯 CPU, 零 token。
/// 这是"远程生成后如果是文本处理任务就可以本地先跑起来"里的本地那一段。
/// </summary>
public sealed class TextProcessExecutor : ILocalNodeExecutor
{
    public string Id => LocalExecutorRegistry.TextProcess;

    public Task<NodeExecutionResult> RunAsync(PlanNode node, LocalNodeContext ctx, CancellationToken ct)
    {
        var text = ResolveInput(node, ctx);
        if (string.IsNullOrEmpty(text) && ctx.ArtifactPath is null)
        {
            return Task.FromResult(PythonSelfTestExecutor.Fail(node.Id,
                "无可用输入 (无上游输出 / 无远程正文 / 无产物) ⇒ 本地处理无对象", NodeFailureKind.Permanent));
        }

        var sb = new StringBuilder();
        sb.Append("本地统计: ");
        if (!string.IsNullOrEmpty(text))
        {
            var lines = text.Split('\n').Length;
            var cjk = text.Count(c => c >= '\u4e00' && c <= '\u9fff');
            sb.Append($"字符={text.Length} 行={lines} 中文={cjk} 词≈{text.Split([' ', '\t', '\n', '\r'], StringSplitOptions.RemoveEmptyEntries).Length} 指纹={Sha(text)}");
        }
        if (ctx.ArtifactPath is { } p && File.Exists(p))
        {
            var fi = new FileInfo(p);
            sb.Append($" | 产物={Path.GetFileName(p)} 字节={fi.Length} 改动={fi.LastWriteTimeUtc:HH:mm:ss}");
        }
        if (ctx.NodeOutputs.Count > 0)
        {
            sb.Append(" | 上游:");
            foreach (var kv in ctx.NodeOutputs)
                sb.Append($" {kv.Key}={(string.IsNullOrEmpty(kv.Value) ? "-" : "有输出")}");
        }

        var summary = sb.ToString();
        AgentTelemetry.Emit("plan_local_text", "PlanRunner",
            ("node", node.Id), ("exec", Id), ("chars", summary.Length), ("tokens", 0L));
        return Task.FromResult(new NodeExecutionResult
        {
            NodeId = node.Id,
            FinalState = PlanNodeState.Completed,
            Output = summary,
        });
    }

    /// <summary>
    /// 输入解析顺序: 上游输出 → **无依赖? 本轮原文** → 远程正文 (确定性, 可单测)。
    /// D4: 无依赖节点的输入是"用户原文"(模型生成前就在手) —— 不许误取生成正文, 否则本地先行
    ///     会变成"处理别人的产物", 语义就错了。
    /// </summary>
    internal static string ResolveInput(PlanNode node, LocalNodeContext ctx)
    {
        // v0.22.0 exp9 D7: 运行时依赖 (执行中发现的) 与声明依赖同权 —— 它是"我确实要它的产出"的显式契约,
        // 排在声明依赖之前解析, 因为它是更晚、更具体的需求 (调度器已保证其产出就绪才会跑到这里)。
        foreach (var dep in node.RuntimeDeps)
        {
            if (ctx.NodeOutputs.TryGetValue(dep, out var ro) && !string.IsNullOrEmpty(ro))
                return ro!;
        }
        foreach (var dep in node.DependsOn)
        {
            if (ctx.NodeOutputs.TryGetValue(dep, out var o) && !string.IsNullOrEmpty(o))
                return o!;
        }
        if (node.DependsOn.Count == 0 && !string.IsNullOrEmpty(ctx.SourceText))
            return ctx.SourceText!;
        return ctx.RemoteText ?? string.Empty;
    }

    internal static string Sha(string s) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(s)))[..8];
}

/// <summary>
/// 计划事件名 (v0.22.0 exp9 D5) —— 前端按事件名订阅; 载荷是手写 JSON (零反射, AOT 安全)。
/// </summary>
public static class PlanEvents
{
    /// <summary>计划已创建 (意图进入即公告: 子任务细分 + 每步位置, 不等模型生成完)</summary>
    public const string Created = "plan.created";

    /// <summary>单节点落终态 (位置/执行器/耗时/token/产物)</summary>
    public const string Node = "plan.node";

    /// <summary>计划收口 (本地先行/重叠/汇总计数)</summary>
    public const string Finished = "plan.finished";
}

/// <summary>
/// 计划事件出站口 (v0.22.0 exp9 D5)。核心层只依赖这个接口; 具体信封与传输由宿主接
/// (host: `FrontendApiContract.FormatEvent` + `FrontendEventHub`)。
///
/// 契约: 实现方抛异常**不得**打断计划 (PlanRunner 仍会兜底), 也不得阻塞主链。
/// </summary>
public interface IPlanEventSink
{
    Task EmitAsync(string @event, string payloadJson, CancellationToken ct = default);
}

/// <summary>单调时钟 (跨平台, 不受系统时间调整影响) —— 用于"本地先行与远程生成真重叠"的测量</summary>
public static class Monotonic
{
    private static readonly double TicksPerUs = Stopwatch.Frequency / 1_000_000.0;

    /// <summary>毫秒 (TickCount64, 跨平台单调): 长时段用</summary>
    public static long NowMs() => Environment.TickCount64;

    /// <summary>微秒 (Stopwatch 计时器): 本地节点常在**亚毫秒**完成 —— 毫秒分辨率会把"真重叠"舍入成 0,
    /// 那就成了假证据 (声称并行先行, 数字却是 0)。</summary>
    public static long NowUs() => (long)(Stopwatch.GetTimestamp() / TicksPerUs);
}

/// <summary>远程生成窗口 (主链事实: 调用方在模型调用前后各取一次单调时刻)</summary>
public readonly record struct RemoteWindow(long StartedUs, long ReadyUs)
{
    public long WaitUs => Math.Max(0, ReadyUs - StartedUs);

    public long WaitMs => WaitUs / 1000;
}

/// <summary>
/// 本地先行批次 (v0.22.0 exp9 D4): 无依赖本地节点的**真并行**执行句柄。
/// 为什么需要句柄: 这些节点的输入 (用户原文) 在远程生成前就在手, 因此可以在模型调用
/// **进行中**就跑完 —— 而不是等远程产物回来再跑 (那是 D3 的串行语义)。
/// </summary>
public sealed class LocalFirstRun
{
    /// <summary>本批次节点 id (前端/KPI 显示"哪些步先跑了")</summary>
    public required IReadOnlyList<string> NodeIds { get; init; }

    /// <summary>批次完成信号 (PlanRunner.RunAsync 会 await 它并复用结果, **绝不重复执行**)</summary>
    public required Task Pending { get; set; }

    public required long StartedUs { get; init; }

    /// <summary>批次结束时刻 (全部无依赖本地节点落终态)</summary>
    public long EndedUs { get; internal set; }

    /// <summary>批次耗时 (微秒): 亚毫秒本地节点必须用 µs 计量, 否则重叠会被舍入成 0</summary>
    public long ElapsedUs => Math.Max(0, EndedUs - StartedUs);

    public int ElapsedMs => (int)(ElapsedUs / 1000);

    internal ConcurrentDictionary<string, NodeOutcome> Outcomes { get; } = new(StringComparer.Ordinal);

    internal ConcurrentDictionary<string, NodeExecutionResult> Results { get; } = new(StringComparer.Ordinal);

    internal void MarkEnded() => EndedUs = Monotonic.NowUs();
}

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
