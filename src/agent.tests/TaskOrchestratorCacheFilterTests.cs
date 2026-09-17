using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using agent.intent;
using agent.registry;
using Xunit;
namespace agent.tests;

/// <summary>
/// R518 运行期缓存排除 (真机自抓缺陷): 节点按题面「写自测并运行」时解释器自动落
/// `__pycache__/*.pyc`, 旧 diff 把它算成「越界写入」⇒ 整链 fail-closed。
/// 本组为**正控 + 负控**成对: 缓存不判越界 (正控), 但真实越界写入/真实产物缺失**判据不许放松** (负控)。
/// </summary>
public sealed class TaskOrchestratorCacheFilterTests
{
    private static string NewWorkspace()
    {
        var d = Path.Combine(Path.GetTempPath(), "r518cache-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(d);
        return d;
    }

    private static Dictionary<string, IReadOnlyList<string>> Scopes(params (string, string[])[] items)
    {
        var m = new Dictionary<string, IReadOnlyList<string>>(StringComparer.Ordinal);
        foreach (var (id, paths) in items) m[id] = paths;
        return m;
    }

    private static TaskOrchestrator Make(string ws, Dictionary<string, IReadOnlyList<string>> scopes, int esc = 0)
        => new(options: new TaskOrchestrator.Options
        {
            NodeMaxSteps = 4,
            MaxBudgetEscalations = esc,
            WorkspaceRoot = ws,
            NodeScopes = scopes,
        });

    private static void Write(string ws, string rel, string body)
    {
        var p = Path.Combine(ws, rel.Replace('/', Path.DirectorySeparatorChar));
        Directory.CreateDirectory(Path.GetDirectoryName(p)!);
        File.WriteAllText(p, body);
    }

    // ── 正控: 缓存写入不算越界, 真实产物在范围内 ⇒ 节点 Completed ──────────────
    [Fact]
    public async Task Pycache_Writes_Are_Not_Scope_Violations()
    {
        var ws = NewWorkspace();
        var orch = Make(ws, Scopes(("n1", new[] { "tasksvc/" })));
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 写 model\n", "c1");

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            Write(ws, "tasksvc/model.py", "x = 1\n");
            Write(ws, "tasksvc/__pycache__/model.cpython-311.pyc", "BYTECODE");
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "好的" });
        });

        Assert.Equal(PlanNodeState.Completed, run.NodeStates["n1"]);
        Assert.Empty(orch.ScopeViolations);
        Assert.Single(orch.NodeArtifacts["n1"]);                        // 只算真实产物
        Assert.Contains("A tasksvc/model.py", orch.NodeArtifacts["n1"]);
    }

    // ── 负控 1: 真实越界写入**仍**判死 (缓存排除不得变成整类豁免) ─────────────
    [Fact]
    public async Task Real_Out_Of_Scope_Write_Still_Fails()
    {
        var ws = NewWorkspace();
        var orch = Make(ws, Scopes(("n1", new[] { "tasksvc/" })));
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 写 model\n", "c1");

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            Write(ws, "tasksvc/model.py", "x = 1\n");
            Write(ws, "kvsvc/server.py", "越界\n");                      // 同类越界: 非缓存
            Write(ws, "tasksvc/__pycache__/model.cpython-311.pyc", "BYTECODE");
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "好的" });
        });

        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n1"]);
        Assert.Contains(orch.ScopeViolations, v => v.Kind == "out_of_scope" && v.Path == "kvsvc/server.py");
        Assert.DoesNotContain(orch.ScopeViolations, v => v.Path.Contains("__pycache__"));
    }

    // ── 负控 2: 只有缓存写入 ⇒ 仍是「零产物」假绿 (缓存不得当产物顶包) ─────────
    [Fact]
    public async Task Cache_Only_Node_Still_Counts_As_No_Artifact()
    {
        var ws = NewWorkspace();
        var orch = Make(ws, Scopes(("n1", new[] { "tasksvc/" })), esc: 1);
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 写 model\n", "c1");
        var calls = 0;

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            calls++;
            Write(ws, "tasksvc/__pycache__/model.cpython-311.pyc", "BYTECODE");
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "好的" });
        });

        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n1"]);
        Assert.Contains(orch.ScopeViolations, v => v.Kind == "no_artifact");
        Assert.Equal(2, calls);                                         // 零产物 ⇒ R518 升预算重试一次
        Assert.Equal(1, orch.Telemetry.Single().Escalations);
    }

    // ── 负控 3: `.pyc` 结尾文件 (无 __pycache__ 目录) 同样排除; 同名源码不排除 ─
    [Fact]
    public async Task Suffix_Rule_Excludes_Only_Bytecode()
    {
        var ws = NewWorkspace();
        var orch = Make(ws, Scopes(("n1", new[] { "tasksvc/model.py" })));   // 文件级范围 (非目录前缀)
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 写 model\n", "c1");

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            Write(ws, "tasksvc/model.py", "x = 1\n");
            Write(ws, "tasksvc/model.pyc", "BYTECODE");                  // 裸 .pyc (范围外) ⇒ 排除
            Write(ws, "tasksvc/notes.md", "# 说明\n");                    // 普通文件 ⇒ 越界
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "好的" });
        });

        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n1"]);
        Assert.Single(orch.ScopeViolations);
        Assert.Equal("tasksvc/notes.md", orch.ScopeViolations[0].Path);
    }
}
