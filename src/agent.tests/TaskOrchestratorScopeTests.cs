using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using agent.intent;
using agent.registry;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R516 节点产物契约判据 (修 R515 两个真机缺陷):
///   H 假绿: 声明了写范围却**零产物**的节点不得记 Completed (R515 真机 n3: 5 ms / 0 产物仍 Completed);
///   I 越界: 写了范围外文件的节点 ⇒ Failed + 违规逐条点名 (提示词约束 → fail-closed 机制);
///   J 起臂前拒收: 同层写范围重叠 / 未知节点 ⇒ 校验期报错 (零 LLM 成本);
///   K 向后兼容: 未声明范围的计划行为不变, 但产物仍被记账 (报告如实标注「未声明」);
///   L 归属唯一: 快照权威只有编排器一个 (宿主不再各自快照 ⇒ 同层写者不会互相覆盖归属)。
/// </summary>
public class TaskOrchestratorScopeTests : IDisposable
{
    private readonly List<string> _tempDirs = new();

    private string NewWorkspace()
    {
        var dir = Path.Combine(Path.GetTempPath(), "r516-ws-" + Guid.NewGuid().ToString("N")[..10]);
        Directory.CreateDirectory(dir);
        _tempDirs.Add(dir);
        return dir;
    }

    public void Dispose()
    {
        foreach (var dir in _tempDirs)
        {
            try { if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true); } catch (IOException) { }
        }
    }

    private static Dictionary<string, IReadOnlyList<string>> Scopes(params (string Node, string[] Paths)[] items)
    {
        var map = new Dictionary<string, IReadOnlyList<string>>(StringComparer.Ordinal);
        foreach (var (node, paths) in items) map[node] = paths;
        return map;
    }

    // ── H 假绿防护 ──────────────────────────────────────────────────────────

    [Fact]
    public async Task Scoped_Node_With_Zero_Artifacts_Fails_Instead_Of_Completed()
    {
        var ws = NewWorkspace();
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 实现 tasksvc 整包\n", "h1");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options
        {
            NodeMaxSteps = 4,
            WorkspaceRoot = ws,
            NodeScopes = Scopes(("n1", new[] { "tasksvc/" })),
        });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
            Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "只回答了 OK" }));

        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n1"]);
        Assert.Contains(orch.Telemetry, t => t.Error.Contains("假绿防护", StringComparison.Ordinal));
        Assert.Contains(orch.ScopeViolations, v => v.NodeId == "n1" && v.Kind == "no_artifact");
        Assert.Empty(orch.NodeArtifacts["n1"]);
    }

    [Fact]
    public async Task Scoped_Node_With_In_Scope_Artifact_Completes_And_Is_Recorded()
    {
        var ws = NewWorkspace();
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 写 model\n", "h2");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options
        {
            NodeMaxSteps = 4,
            WorkspaceRoot = ws,
            NodeScopes = Scopes(("n1", new[] { "tasksvc/" })),
        });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            Directory.CreateDirectory(Path.Combine(ws, "tasksvc"));
            File.WriteAllText(Path.Combine(ws, "tasksvc", "model.py"), "x = 1\n");
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "done" });
        });

        Assert.Equal(PlanNodeState.Completed, run.NodeStates["n1"]);
        Assert.Empty(orch.ScopeViolations);
        Assert.Contains("A tasksvc/model.py", orch.NodeArtifacts["n1"]);
        Assert.Contains(orch.Telemetry, t => t.NodeId == "n1" && t.Scope.SequenceEqual(new[] { "tasksvc/" }));
    }

    // ── I 越界写 ────────────────────────────────────────────────────────────

    [Fact]
    public async Task Out_Of_Scope_Write_Fails_Node_And_Names_The_Path()
    {
        var ws = NewWorkspace();
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 写 model\n", "i1");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options
        {
            NodeMaxSteps = 4,
            WorkspaceRoot = ws,
            NodeScopes = Scopes(("n1", new[] { "tasksvc/" })),
        });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            Directory.CreateDirectory(Path.Combine(ws, "tasksvc"));
            File.WriteAllText(Path.Combine(ws, "tasksvc", "model.py"), "x = 1\n");
            File.WriteAllText(Path.Combine(ws, "rogue.py"), "y = 2\n");   // 越界写
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "done" });
        });

        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n1"]);
        Assert.Contains(orch.ScopeViolations, v => v.Kind == "out_of_scope" && v.Path == "rogue.py");
        Assert.Contains(orch.Telemetry, t => t.Error.Contains("越界写入", StringComparison.Ordinal) && t.Error.Contains("rogue.py", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Out_Of_Scope_Deletion_Is_Also_A_Violation()
    {
        var ws = NewWorkspace();
        File.WriteAllText(Path.Combine(ws, "keep.txt"), "原有文件\n");
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 只许写 out/\n", "i2");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options
        {
            NodeMaxSteps = 4,
            WorkspaceRoot = ws,
            NodeScopes = Scopes(("n1", new[] { "out/" })),
        });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            Directory.CreateDirectory(Path.Combine(ws, "out"));
            File.WriteAllText(Path.Combine(ws, "out", "a.txt"), "ok\n");
            File.Delete(Path.Combine(ws, "keep.txt"));                    // 越界删
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "done" });
        });

        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n1"]);
        Assert.Contains(orch.ScopeViolations, v => v.Kind == "out_of_scope" && v.Path == "keep.txt");
    }

    [Fact]
    public async Task Local_Node_Is_Also_Bound_By_Scope_Evidence()
    {
        var ws = NewWorkspace();
        var (plan, _) = TaskPlanFile.ParseText("l1 | | local | test.write | out/l1.txt\n", "i3");
        var orch = new TaskOrchestrator(new[] { new WritingLocalExecutor() }, options: new TaskOrchestrator.Options
        {
            NodeMaxSteps = 4,
            WorkspaceRoot = ws,
            NodeScopes = Scopes(("l1", new[] { "out/" })),
            LocalContextFactory = node => new LocalNodeContext
            {
                SessionId = "r516",
                ArtifactPath = Path.Combine(ws, node.LocalHint ?? node.Text),
                PythonPath = "python3",
            },
        });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
            Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed }));

        Assert.Equal(PlanNodeState.Completed, run.NodeStates["l1"]);
        Assert.Contains("A out/l1.txt", orch.NodeArtifacts["l1"]);
    }

    private sealed class WritingLocalExecutor : ILocalNodeExecutor
    {
        public string Id => "test.write";
        public Task<NodeExecutionResult> RunAsync(PlanNode node, LocalNodeContext ctx, CancellationToken ct)
        {
            var dir = Path.GetDirectoryName(ctx.ArtifactPath);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir!);
            File.WriteAllText(ctx.ArtifactPath, "l1\n");
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed });
        }
    }

    // ── K 向后兼容 (前态锚: 未声明范围 ⇒ 旧行为保持) ─────────────────────────

    [Fact]
    public async Task Unscoped_Node_With_Zero_Artifacts_Stays_Completed_Pre_R516_Anchor()
    {
        var ws = NewWorkspace();
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 一\n", "k1");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options { NodeMaxSteps = 4, WorkspaceRoot = ws });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
            Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "ok" }));

        Assert.Equal(PlanNodeState.Completed, run.NodeStates["n1"]);
        Assert.Empty(orch.ScopeViolations);
        Assert.Empty(orch.NodeArtifacts["n1"]);
        Assert.Empty(orch.Telemetry.Single().Scope);
    }

    [Fact]
    public async Task Without_Workspace_Root_Legacy_Path_Stays_Untouched()
    {
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 一\n", "k2");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options { NodeMaxSteps = 4 });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
            Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "ok" }));

        Assert.Equal(PlanNodeState.Completed, run.NodeStates["n1"]);
        Assert.Empty(orch.NodeArtifacts);
    }

    // ── J 起臂前拒收 (零 LLM 成本) ──────────────────────────────────────────

    [Fact]
    public void Same_Level_Overlapping_Scopes_Are_Rejected_Before_Any_Call()
    {
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 整包A\nn2 | | remote | | 整包B\n", "j1");
        var problems = TaskOrchestrator.ValidateScopes(plan!, Scopes(("n1", new[] { "tasksvc/" }), ("n2", new[] { "tasksvc/model.py" })));

        Assert.Contains(problems, p => p.Contains("同层节点 n1/n2", StringComparison.Ordinal) && p.Contains("重叠", StringComparison.Ordinal));
    }

    [Fact]
    public void Same_Level_Disjoint_Scopes_And_Cross_Level_Overlap_Are_Allowed()
    {
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | A\nn2 | | remote | | B\nn3 | n1 | remote | | C\n", "j2");
        var disjoint = TaskOrchestrator.ValidateScopes(plan!, Scopes(("n1", new[] { "tasksvc/model.py" }), ("n2", new[] { "tasksvc/cli.py" })));
        Assert.Empty(disjoint);

        // 跨层 (L0 → L1) 是串行 ⇒ 同文件允许; 但同层仍须互斥
        var crossLevel = TaskOrchestrator.ValidateScopes(plan!, Scopes(("n1", new[] { "tasksvc/" }), ("n3", new[] { "tasksvc/model.py" })));
        Assert.Empty(crossLevel);
    }

    [Fact]
    public void Sibling_Prefix_Is_Not_Treated_As_Overlap()
    {
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | A\nn2 | | remote | | B\n", "j3");
        var problems = TaskOrchestrator.ValidateScopes(plan!, Scopes(("n1", new[] { "out/" }), ("n2", new[] { "out2/x.py" })));
        Assert.Empty(problems);
    }

    [Fact]
    public void Unknown_Node_In_Scope_File_Is_Rejected()
    {
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | A\n", "j4");
        var problems = TaskOrchestrator.ValidateScopes(plan!, Scopes(("n9", new[] { "out/" })));
        Assert.Contains(problems, p => p.Contains("未知节点 n9", StringComparison.Ordinal));
    }

    [Theory]
    [InlineData("/etc/passwd")]
    [InlineData("../outside.txt")]
    [InlineData("a/../../b.txt")]
    public void Scope_Paths_Outside_Workspace_Are_Rejected(string bad)
    {
        var (scopes, problems) = NodeScopeFile.ParseText("n1 | " + bad + "\n");
        Assert.Null(scopes);
        Assert.Contains(problems, p => p.Contains("路径越界", StringComparison.Ordinal));
    }

    [Fact]
    public void Scope_File_Parses_Comments_And_Reports_Empty()
    {
        var (scopes, problems) = NodeScopeFile.ParseText("# 注释\n\nn1 | a.py, b/\n");
        Assert.Empty(problems);
        Assert.Equal(new[] { "a.py", "b/" }, scopes!["n1"]);

        var (none, noneProblems) = NodeScopeFile.ParseText("# 只有注释\n");
        Assert.Null(none);
        Assert.NotEmpty(noneProblems);
    }

    [Theory]
    [InlineData("tasksvc/", "tasksvc/model.py", true)]
    [InlineData("tasksvc/", "tasksvc/sub/deep.py", true)]
    [InlineData("tasksvc/", "tasksvc2/model.py", false)]
    [InlineData("tasksvc/*.py", "tasksvc/model.py", true)]
    [InlineData("tasksvc/*.py", "tasksvcs/model.py", false)]
    [InlineData("a.py", "a.py", true)]
    [InlineData("a.py", "b.py", false)]
    public void Scope_Matching_Semantics(string pattern, string path, bool expected)
        => Assert.Equal(expected, NodeScopeFile.InScope(new[] { NodeScopeFile.Normalize(pattern) }, path));
}
