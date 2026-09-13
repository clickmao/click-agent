using System.Collections.Concurrent;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
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
    public string? ArtifactPath { get; init; }

    /// <summary>本轮远程生成正文 (Hybrid 节点的第二段输入; 主链产出, 不重复调用模型)</summary>
    public string? RemoteText { get; init; }

    /// <summary>远程产物是否已就绪 (未就绪 ⇒ 依赖它的本地节点不许假装成功)</summary>
    public bool HasRemoteProduct => !string.IsNullOrEmpty(ArtifactPath) || !string.IsNullOrEmpty(RemoteText);

    public string? SessionId { get; init; }

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

    /// <summary>输入解析顺序: 上游输出 → 远程正文 (确定性, 可单测)</summary>
    internal static string ResolveInput(PlanNode node, LocalNodeContext ctx)
    {
        foreach (var dep in node.DependsOn)
        {
            if (ctx.NodeOutputs.TryGetValue(dep, out var o) && !string.IsNullOrEmpty(o))
                return o!;
        }
        return ctx.RemoteText ?? string.Empty;
    }

    internal static string Sha(string s) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(s)))[..8];
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

    public PlanRunner(
        IEnumerable<ILocalNodeExecutor>? executors = null,
        PythonArtifactLedger? ledger = null,
        Func<bool>? gate = null)
    {
        var list = executors?.ToList() ?? [new PythonSelfTestExecutor(), new TextProcessExecutor()];
        _executors = list.ToDictionary(e => e.Id, StringComparer.Ordinal);
        _ledger = ledger;
        _gate = gate ?? (() => IsEnabled());
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
    /// 从产物台账构造上下文 (取最近一条 python 报告 = 刚落盘的产物)。
    /// 诚实边界: 台账无会话维度, 跨会话并发时取"最新一条"; 会话级隔离属 D5。
    /// </summary>
    public LocalNodeContext ContextFromLedger(string? sessionId = null, string? remoteText = null)
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
        };
    }

    /// <summary>执行整张计划 (真执行体)。返回的 run.Outcomes 即前端/KPI 的唯一事实源。</summary>
    public async Task<TaskPlanRun> RunAsync(TaskPlan plan, LocalNodeContext? ctx = null, CancellationToken ct = default)
    {
        ctx ??= new LocalNodeContext();
        var enabled = _gate();
        var outcomes = new ConcurrentDictionary<string, NodeOutcome>(StringComparer.Ordinal);

        Func<PlanNode, CancellationToken, Task<NodeExecutionResult>> runner = enabled
            ? (node, c) => RunNodeAsync(node, ctx, outcomes, c)
            : (node, _) =>
            {
                // 哑体回退也要留审计行 (state=Skipped + 原因), 否则 run.Outcomes 空白 = 静默
                outcomes[node.Id] = DummyOutcome(node);
                return Task.FromResult(Dummy(node));
            };

        var sw = Stopwatch.StartNew();
        var executor = new TaskPlanExecutor(runner);
        var run = await executor.ExecuteAsync(plan, pollInjections: null, ct).ConfigureAwait(false);
        sw.Stop();

        // 审计与状态对齐: 只保留真正跑过的节点 (Paused/待澄清节点无产物, 不塞假数据)
        run.Outcomes = plan.Nodes
            .Where(n => outcomes.ContainsKey(n.Id))
            .Select(n => outcomes[n.Id])
            .ToList();

        var local = run.Outcomes.Count(o => o.Location is "local" or "hybrid" && o.State == PlanNodeState.Completed);
        var failed = run.Outcomes.Count(o => o.State == PlanNodeState.Failed);
        var skipped = run.Outcomes.Count(o => o.State == PlanNodeState.Skipped);
        AgentTelemetry.Emit("plan", "PlanRunner",
            ("plan_id", plan.PlanId),
            ("enabled", enabled),
            ("nodes", plan.Nodes.Count),
            ("local_ok", local),
            ("local_failed", failed),
            ("skipped", skipped),
            ("local_tokens", 0L),
            ("elapsed_ms", sw.ElapsedMilliseconds));
        return run;
    }

    private async Task<NodeExecutionResult> RunNodeAsync(
        PlanNode node, LocalNodeContext ctx, ConcurrentDictionary<string, NodeOutcome> outcomes, CancellationToken ct)
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
        outcomes[node.Id] = new NodeOutcome
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

        AgentTelemetry.Emit("plan_node", "PlanRunner",
            ("plan_node", node.Id),
            ("intent", node.Intent),
            ("loc", node.LocationText),
            ("exec", node.LocalExecutorId ?? "-"),
            ("state", result.FinalState.ToString()),
            ("elapsed_ms", sw.ElapsedMilliseconds),
            ("tokens", tokens));

        return result;
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
