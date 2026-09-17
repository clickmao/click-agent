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
/// R518 节点预算自适应判据 (候选②; 修 R517 真机「零产物 ⇒ 节点 Failed ⇒ 整链无产物」):
///   M 升级面: 远端节点「声明了范围却零产物」⇒ 同节点**升预算重试** (2 倍, 上界 32) ⇒ 重试产出范围内文件 ⇒ 节点 Completed;
///   N 负控-真失败不掩盖: 越界写 / 非零产物失败**不许**重试 (编排器不得用重试把真失败洗成偶然);
///   O 有界: 重试次数 = MaxBudgetEscalations, 预算封顶 32, 重试后仍零产物 ⇒ Failed + 恰 1 条 no_artifact 记账 (不重复计数);
///   P 前态锚: MaxBudgetEscalations 缺省 = 0 ⇒ 旧行为逐字不动 (R516/R517 既有控制不受本轮改动影响);
///   Q 本地节点不重试 (零 LLM 通道; 无「步数预算」语义);
///   R 记账: 报告面 BudgetSteps/Escalations/Attempts + 有效预算上界, 重试不许静默。
/// </summary>
public class TaskOrchestratorBudgetTests : IDisposable
{
    private readonly List<string> _tempDirs = new();

    private string NewWorkspace()
    {
        var dir = Path.Combine(Path.GetTempPath(), "r518-ws-" + Guid.NewGuid().ToString("N")[..10]);
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

    /// <summary>记录每次远端调用的步数预算 (重试留痕的观测面)。</summary>
    private sealed class StepSpy
    {
        public List<int> Steps { get; } = new();
    }

    // ── M 升级面 (正控) ─────────────────────────────────────────────────────

    [Fact]
    public async Task Zero_Artifact_Node_Escalates_Once_Then_Completes()
    {
        var ws = NewWorkspace();
        var spy = new StepSpy();
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 写 model\n", "m1");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options
        {
            NodeMaxSteps = 4,
            MaxBudgetEscalations = 1,
            WorkspaceRoot = ws,
            NodeScopes = Scopes(("n1", new[] { "tasksvc/" })),
        });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            spy.Steps.Add(steps);
            if (steps <= 4)   // 首跑: 只回答不落盘 (R517 真机败法)
                return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "好的" });
            Directory.CreateDirectory(Path.Combine(ws, "tasksvc"));
            File.WriteAllText(Path.Combine(ws, "tasksvc", "model.py"), "x = 1\n");
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "done" });
        });

        Assert.Equal(new[] { 4, 8 }, spy.Steps);                       // 重试 = 同节点 2 倍预算
        Assert.Equal(PlanNodeState.Completed, run.NodeStates["n1"]);
        Assert.Empty(orch.ScopeViolations);                            // 成功路径不留违规
        Assert.Contains("A tasksvc/model.py", orch.NodeArtifacts["n1"]);

        var t = orch.Telemetry.Single(x => x.NodeId == "n1");
        Assert.Equal(8, t.BudgetSteps);
        Assert.Equal(1, t.Escalations);
        Assert.Equal(new[] { "4:Failed", "8:Completed" }, t.Attempts);
        Assert.Equal(1, orch.EscalationCount);
    }

    // ── N 负控: 真失败不许被重试掩盖 ────────────────────────────────────────

    [Fact]
    public async Task Out_Of_Scope_Failure_Is_Not_Retried()
    {
        var ws = NewWorkspace();
        var spy = new StepSpy();
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 写 model\n", "n2");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options
        {
            NodeMaxSteps = 4,
            MaxBudgetEscalations = 3,   // 即使允许 3 次, 越界写也不许重试
            WorkspaceRoot = ws,
            NodeScopes = Scopes(("n1", new[] { "tasksvc/" })),
        });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            spy.Steps.Add(steps);
            Directory.CreateDirectory(Path.Combine(ws, "tasksvc"));
            File.WriteAllText(Path.Combine(ws, "tasksvc", "model.py"), "x = 1\n");
            File.WriteAllText(Path.Combine(ws, "rogue.py"), "y = 2\n");
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "done" });
        });

        Assert.Equal(new[] { 4 }, spy.Steps);
        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n1"]);
        Assert.Contains(orch.ScopeViolations, v => v.NodeId == "n1" && v.Kind == "out_of_scope");
        Assert.Equal(0, orch.EscalationCount);
        Assert.Equal(new[] { "4:Failed" }, orch.Telemetry.Single().Attempts);
    }

    [Fact]
    public async Task Non_Artifact_Failure_Is_Not_Retried()
    {
        var ws = NewWorkspace();
        var spy = new StepSpy();
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 写 model\n", "n3");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options
        {
            NodeMaxSteps = 4,
            MaxBudgetEscalations = 2,
            WorkspaceRoot = ws,
            NodeScopes = Scopes(("n1", new[] { "tasksvc/" })),
        });

        // 远端自己报 Failed (无效 Key / 超时类): 与「零产物」不同因 ⇒ 不升预算
        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            spy.Steps.Add(steps);
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Failed, Error = "远端不可用" });
        });

        Assert.Equal(new[] { 4 }, spy.Steps);
        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n1"]);
        Assert.Empty(orch.ScopeViolations);
    }

    // ── O 有界 + 记账不重复 ─────────────────────────────────────────────────

    [Fact]
    public async Task Escalation_Is_Bounded_And_Records_Single_NoArtifact()
    {
        var ws = NewWorkspace();
        var spy = new StepSpy();
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 写 model\n", "o1");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options
        {
            NodeMaxSteps = 4,
            MaxBudgetEscalations = 1,
            WorkspaceRoot = ws,
            NodeScopes = Scopes(("n1", new[] { "tasksvc/" })),
        });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            spy.Steps.Add(steps);
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "好的" });
        });

        Assert.Equal(new[] { 4, 8 }, spy.Steps);                       // 1 次重试后停手 (不许无界)
        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n1"]);
        Assert.Single(orch.ScopeViolations.Where(v => v.Kind == "no_artifact"));   // 同因只记一条
        Assert.Equal(new[] { "4:Failed", "8:Failed" }, orch.Telemetry.Single().Attempts);
    }

    [Fact]
    public async Task Escalated_Budget_Never_Exceeds_Action_Loop_Ceiling()
    {
        var ws = NewWorkspace();
        var spy = new StepSpy();
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 写 model\n", "o2");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options
        {
            NodeMaxSteps = 20,
            MaxBudgetEscalations = 2,
            WorkspaceRoot = ws,
            NodeScopes = Scopes(("n1", new[] { "tasksvc/" })),
        });

        await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            spy.Steps.Add(steps);
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "好的" });
        });

        Assert.Equal(new[] { 20, 32 }, spy.Steps);                     // 2 倍会到 40 ⇒ 封顶 32
        Assert.All(spy.Steps, s => Assert.True(s <= TaskOrchestrator.MaxNodeBudget));
        // 有效预算上界 = Σ 逐节点**最终**预算 (单节点: 20→32 = 32); 基线口径仍 = 未含重试 (20)
        Assert.Equal(32, orch.BudgetCeilingEffective);
        Assert.Equal(20, orch.BudgetCeiling);
        Assert.Equal(32, orch.Telemetry.Single().BudgetSteps);
        Assert.Equal(1, orch.Telemetry.Single().Escalations);
    }

    // ── P 前态锚: 缺省关闭 ⇒ 旧行为逐字不动 ────────────────────────────────

    [Fact]
    public async Task Default_Options_Do_Not_Escalate_Pre_R518_Anchor()
    {
        var ws = NewWorkspace();
        var spy = new StepSpy();
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 写 model\n", "p1");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options
        {
            NodeMaxSteps = 4,                       // 未设 MaxBudgetEscalations ⇒ 0
            WorkspaceRoot = ws,
            NodeScopes = Scopes(("n1", new[] { "tasksvc/" })),
        });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            spy.Steps.Add(steps);
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "好的" });
        });

        Assert.Equal(new[] { 4 }, spy.Steps);
        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n1"]);
        Assert.Equal(0, orch.Telemetry.Single().Escalations);
        Assert.Equal(4, orch.Telemetry.Single().BudgetSteps);
        Assert.Equal(new[] { "4:Failed" }, orch.Telemetry.Single().Attempts);
    }

    // ── Q 本地节点不重试 ────────────────────────────────────────────────────

    [Fact]
    public async Task Local_Node_Is_Never_Escalated()
    {
        var ws = NewWorkspace();
        var calls = 0;
        var (plan, _) = TaskPlanFile.ParseText("l1 | | local | test.noop | out/l1.txt\n", "q1");
        var orch = new TaskOrchestrator(new ILocalNodeExecutor[] { new NoopLocalExecutor(() => calls++) },
            options: new TaskOrchestrator.Options
            {
                NodeMaxSteps = 4,
                MaxBudgetEscalations = 3,
                WorkspaceRoot = ws,
                NodeScopes = Scopes(("l1", new[] { "out/" })),
                LocalContextFactory = node => new LocalNodeContext
                {
                    SessionId = "r518",
                    ArtifactPath = Path.Combine(ws, node.LocalHint ?? node.Text),
                    PythonPath = "python3",
                },
            });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
            Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed }));

        Assert.Equal(1, calls);
        Assert.Equal(PlanNodeState.Failed, run.NodeStates["l1"]);
        Assert.Equal(0, orch.EscalationCount);
    }

    private sealed class NoopLocalExecutor : ILocalNodeExecutor
    {
        private readonly Action _onCall;
        public NoopLocalExecutor(Action onCall) => _onCall = onCall;
        public string Id => "test.noop";
        public Task<NodeExecutionResult> RunAsync(PlanNode node, LocalNodeContext ctx, CancellationToken ct)
        {
            _onCall();
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed });
        }
    }

    // ── 选项校验 (fail-closed) ─────────────────────────────────────────────

    [Theory]
    [InlineData(-1)]
    [InlineData(4)]
    public void Options_Reject_Out_Of_Range_Escalations(int n)
        => Assert.Throws<ArgumentOutOfRangeException>(() => new TaskOrchestrator(
            options: new TaskOrchestrator.Options { MaxBudgetEscalations = n }));

    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(3)]
    public void Options_Accept_In_Range_Escalations(int n)
        => Assert.Equal(n, new TaskOrchestrator(options: new TaskOrchestrator.Options { MaxBudgetEscalations = n }).Opt.MaxBudgetEscalations);
}
