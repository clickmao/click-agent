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
