using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.intent;
using agent.registry;
using Xunit;
namespace agent.tests;

/// <summary>
/// R515 长任务编排器判据 (铁律: 每条断言绑定组件**真实行为**, 不是形状检查):
///   A 计划文件解析/校验 fail-closed;
///   B 逐节点真执行 + 上游产出注入下游;
///   C 本地节点与远端节点**真并发** (墙钟重叠可测);
///   D 失败不静默 (失败节点 ⇒ 依赖节点 Skipped);
///   E 每节点预算独立 (预算上界 = 远端节点数 × 单节点预算);
///   F 逐节点事件 (Running + 终态);
///   G 跨轮续作 (seedRun: 已 Completed 不重跑, 半途态重跑)。
/// </summary>
public class TaskOrchestratorTests
{
    private sealed class FakeLocal : ILocalNodeExecutor
    {
        private readonly int _delayMs;
        public FakeLocal(string id, int delayMs = 0) { Id = id; _delayMs = delayMs; }
        public string Id { get; }
        public List<string> Ran { get; } = new();
        public async Task<NodeExecutionResult> RunAsync(PlanNode node, LocalNodeContext ctx, CancellationToken ct)
        {
            if (_delayMs > 0) await Task.Delay(_delayMs, ct);
            Ran.Add(node.Id);
            return new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "local:" + node.Id };
        }
    }

    private sealed class FakeSink : IPlanEventSink
    {
        public List<(string Event, string Payload)> Events { get; } = new();
        public Task EmitAsync(string @event, string payloadJson, CancellationToken ct = default)
        {
            Events.Add((@event, payloadJson));
            return Task.CompletedTask;
        }
    }

    // ── A 计划文件 ───────────────────────────────────────────────────────────

    [Fact]
    public void Dsl_Parses_Nodes_And_Computes_Dependency_Levels()
    {
        var (plan, problems) = TaskPlanFile.ParseText(
            "n1 |      | remote |                 | 第一段\n" +
            "n2 | n1   | remote |                 | 第二段\n" +
            "n3 | n2   | local  | python.selftest | out/app.py\n");

        Assert.Empty(problems);
        Assert.NotNull(plan);
        Assert.Equal(3, plan!.Nodes.Count);
        Assert.Equal(0, plan.Nodes.Single(n => n.Id == "n1").Level);
        Assert.Equal(1, plan.Nodes.Single(n => n.Id == "n2").Level);
        Assert.Equal(2, plan.Nodes.Single(n => n.Id == "n3").Level);
        Assert.Equal(NodeExecutionLocation.Local, plan.Nodes.Single(n => n.Id == "n3").Location);
    }

    [Theory]
    [InlineData("n1 | n9 | remote | | 文本\n", "未知节点")]
    [InlineData("n1 | | remote | | 文本\nn1 | | remote | | 文本2\n", "重复")]
    [InlineData("n1 | n2 | remote | | A\nn2 | n1 | remote | | B\n", "成环")]
    [InlineData("n1 | | local | | A\n", "缺执行器")]
    [InlineData("n1 | | remote | python.selftest | A\n", "不应带执行器")]
    [InlineData("n1 | | remote | A\n", "字段数")]
    [InlineData("{\"Nodes\":[]}", "字段数")]
    public void Dsl_Rejects_Invalid_Plans(string text, string expectFragment)
    {
        var (plan, problems) = TaskPlanFile.ParseText(text, "p");
        Assert.Null(plan);
        Assert.Contains(problems, p => p.Contains(expectFragment, StringComparison.Ordinal));
    }

    [Fact]
    public void Dsl_Keeps_Pipe_Characters_Inside_Node_Text()
    {
        var (plan, problems) = TaskPlanFile.ParseText("n1 | | remote | | 视图 open|done|expired|all 互斥\n", "pp");
        Assert.Empty(problems);
        Assert.Equal("视图 open|done|expired|all 互斥", plan!.Nodes[0].Text);
        Assert.Contains("open|done", TaskPlanFile.Render(plan));
    }

    [Fact]
    public void E2e_Plan_Asset_Loads_And_Has_Expected_Shape()
    {
        var path = FindRepoFile("eval/rover/r515/plan-p4.txt");
        if (path is null) return;   // 资产未随测试交付 ⇒ 不误报
        var (plan, problems) = TaskPlanFile.Load(path);
        Assert.Empty(problems);
        Assert.NotNull(plan);
        Assert.Equal(4, plan!.Nodes.Count);
        Assert.Equal(2, plan.Nodes.Count(n => n.Level == 0));                       // n1/n2 同层 ⇒ 可并发
        Assert.Single(plan.Nodes.Where(n => n.Location == NodeExecutionLocation.Local));
        Assert.Contains(plan.Nodes, n => n.Id == "n3" && n.DependsOn.Count == 2);
    }

    private static string? FindRepoFile(string relative)
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, relative);
            if (File.Exists(candidate)) return candidate;
            dir = dir.Parent;
        }
        return null;
    }

    [Fact]
    public void Json_Plan_Roundtrips_Through_Shared_Context()
    {
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 生成\nn2 | n1 | local | text.process | 汇总\n", "p-json");
        var path = Path.Combine(Path.GetTempPath(), "r515-plan-" + Guid.NewGuid().ToString("N")[..8] + ".json");
        File.WriteAllText(path, TaskPlanJsonContext.ToJson(plan!), new UTF8Encoding(false));
        try
        {
            var (loaded, problems) = TaskPlanFile.Load(path);
            Assert.Empty(problems);
            Assert.NotNull(loaded);
            Assert.Equal(2, loaded!.Nodes.Count);
            Assert.Equal("n1", loaded.Nodes[0].Id);
            Assert.Equal("n1", loaded.Nodes[1].DependsOn.Single());
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void Load_Reports_Unreadable_File_Instead_Of_Throwing()
    {
        var (plan, problems) = TaskPlanFile.Load(Path.Combine(Path.GetTempPath(), "r515-none-" + Guid.NewGuid().ToString("N")[..8]));
        Assert.Null(plan);
        Assert.Contains("不可读", problems[0]);
    }

    // ── B/E 逐节点真执行 + 预算上界 ──────────────────────────────────────────

    [Fact]
    public async Task Orchestrator_Runs_Every_Node_And_Injects_Upstream_Output()
    {
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 一\nn2 | n1 | remote | | 二\n", "p1");
        var calls = new List<string>();
        var seenUpstream = new Dictionary<string, string>(StringComparer.Ordinal);
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options { NodeMaxSteps = 7 });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            calls.Add(node.Id);
            Assert.Equal(7, steps);
            seenUpstream[node.Id] = string.Join(",", upstream.Keys);
            return Task.FromResult(new NodeExecutionResult
            {
                NodeId = node.Id,
                FinalState = PlanNodeState.Completed,
                Output = "output-of-" + node.Id,
            });
        });

        Assert.Equal(new[] { "n1", "n2" }, calls.OrderBy(x => x, StringComparer.Ordinal));
        Assert.Equal("", seenUpstream["n1"]);
        Assert.Equal("n1", seenUpstream["n2"]);
        Assert.All(run.NodeStates.Values, s => Assert.Equal(PlanNodeState.Completed, s));
        Assert.Equal(2 * 7, orch.BudgetCeiling);
    }

    // ── C 本地与远端真并发 ──────────────────────────────────────────────────

    [Fact]
    public async Task Orchestrator_Overlaps_Local_And_Remote_Nodes_On_Same_Level()
    {
        var (plan, _) = TaskPlanFile.ParseText(
            "r1 | | remote | | 远端生成 (慢)\n" +
            "l1 | | local  | test.sleep | 本地自测 (同层)\n", "p2");
        var local = new FakeLocal("test.sleep", delayMs: 80);
        var orch = new TaskOrchestrator(new[] { local }, options: new TaskOrchestrator.Options { NodeMaxSteps = 6 });

        var run = await orch.RunAsync(plan!, async (node, upstream, steps, ct) =>
        {
            await Task.Delay(120, ct);
            return new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "remote" };
        });

        Assert.Equal(PlanNodeState.Completed, run.NodeStates["r1"]);
        Assert.Equal(PlanNodeState.Completed, run.NodeStates["l1"]);
        Assert.Equal(new[] { "l1" }, local.Ran);
        // 真并发判据: 墙钟重叠 > 0 (若串行, 两个窗口不交 ⇒ 0)
        Assert.True(orch.OverlapMs > 0, $"未观察到本地/远端重叠: overlap={orch.OverlapMs}ms");
        Assert.Equal(2, orch.Telemetry.Count);
        Assert.Contains(orch.Telemetry, t => t.IsLocal && t.Executor == "test.sleep");
        Assert.Contains(orch.Telemetry, t => !t.IsLocal && t.Executor == "agent-turn");
    }

    // ── D 失败不静默 ────────────────────────────────────────────────────────

    [Fact]
    public async Task Orchestrator_Failed_Node_Skips_Dependents()
    {
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 一\nn2 | n1 | remote | | 二\n", "p3");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options { NodeMaxSteps = 6 });
        var calls = new List<string>();

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            calls.Add(node.Id);
            return Task.FromResult(new NodeExecutionResult
            {
                NodeId = node.Id,
                FinalState = node.Id == "n1" ? PlanNodeState.Failed : PlanNodeState.Completed,
                Error = node.Id == "n1" ? "注入失败" : null,
                FailureKind = NodeFailureKind.Permanent,
            });
        });

        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n1"]);
        Assert.Equal(PlanNodeState.Skipped, run.NodeStates["n2"]);
        Assert.Equal(new[] { "n1" }, calls);
        Assert.Contains(orch.Telemetry, t => t.NodeId == "n1" && t.State == "Failed" && t.Error.Contains("注入失败", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Orchestrator_Local_Executor_Missing_Fails_Node_Instead_Of_Silent_Skip()
    {
        var (plan, _) = TaskPlanFile.ParseText("l1 | | local | not.registered | 产物路径\n", "p4");
        var orch = new TaskOrchestrator(Array.Empty<ILocalNodeExecutor>(), options: new TaskOrchestrator.Options { NodeMaxSteps = 6 });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
            Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed }));

        Assert.Equal(PlanNodeState.Failed, run.NodeStates["l1"]);
        Assert.Contains(orch.Telemetry, t => t.Error.Contains("本地执行器缺失", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Orchestrator_Rejects_Plan_Over_Node_Cap()
    {
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 一\nn2 | | remote | | 二\n", "p5");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options { NodeMaxSteps = 6, MaxNodes = 1 });
        await Assert.ThrowsAsync<ArgumentException>(() =>
            orch.RunAsync(plan!, (n, u, s, ct) => Task.FromResult(new NodeExecutionResult { NodeId = n.Id, FinalState = PlanNodeState.Completed })));
    }

    [Fact]
    public void Orchestrator_Rejects_Out_Of_Range_Node_Steps()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => new TaskOrchestrator(options: new TaskOrchestrator.Options { NodeMaxSteps = 0 }));
        Assert.Throws<ArgumentOutOfRangeException>(() => new TaskOrchestrator(options: new TaskOrchestrator.Options { NodeMaxSteps = 33 }));
    }

    // ── F 逐节点事件 ────────────────────────────────────────────────────────

    [Fact]
    public async Task Orchestrator_Emits_Running_And_Final_Event_Per_Node()
    {
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 一\n", "p6");
        var sink = new FakeSink();
        var orch = new TaskOrchestrator(events: sink, options: new TaskOrchestrator.Options { NodeMaxSteps = 6 });

        await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
            Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "x" }));

        Assert.Equal(2, sink.Events.Count);
        Assert.All(sink.Events, e => Assert.Equal("plan.node", e.Event));
        Assert.Contains("\"state\":\"Running\"", sink.Events[0].Payload);
        Assert.Contains("\"state\":\"Completed\"", sink.Events[1].Payload);
        Assert.Contains("\"node_id\":\"n1\"", sink.Events[0].Payload);
        Assert.Contains("\"location\":\"remote\"", sink.Events[0].Payload);
    }

    [Fact]
    public async Task Orchestrator_Survives_Event_Sink_Throwing()
    {
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 一\n", "p7");
        var orch = new TaskOrchestrator(events: new ThrowingSink(), options: new TaskOrchestrator.Options { NodeMaxSteps = 6 });

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
            Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "x" }));

        Assert.Equal(PlanNodeState.Completed, run.NodeStates["n1"]);
    }

    private sealed class ThrowingSink : IPlanEventSink
    {
        public Task EmitAsync(string @event, string payloadJson, CancellationToken ct = default)
            => throw new InvalidOperationException("事件出口故障");
    }

    // ── G 跨轮续作 ──────────────────────────────────────────────────────────

    [Fact]
    public async Task Orchestrator_SeedRun_Skips_Completed_Node_And_Reruns_Pending()
    {
        var (plan, _) = TaskPlanFile.ParseText("n1 | | remote | | 一\nn2 | n1 | remote | | 二\n", "p8");
        var orch = new TaskOrchestrator(options: new TaskOrchestrator.Options { NodeMaxSteps = 6 });
        var calls = new List<string>();
        var seed = new TaskPlanRun { PlanId = plan!.PlanId };
        seed.NodeStates["n1"] = PlanNodeState.Completed;
        seed.NodeStates["n2"] = PlanNodeState.Running;

        var run = await orch.RunAsync(plan!, (node, upstream, steps, ct) =>
        {
            calls.Add(node.Id);
            return Task.FromResult(new NodeExecutionResult { NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "o" });
        }, seedRun: seed);

        Assert.Equal(new[] { "n2" }, calls);   // n1 已完成 ⇒ 不重跑 (避免重复副作用)
        Assert.Equal(PlanNodeState.Completed, run.NodeStates["n1"]);
        Assert.Equal(PlanNodeState.Completed, run.NodeStates["n2"]);
    }
}
