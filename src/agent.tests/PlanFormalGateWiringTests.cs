using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using agent.intent;
using agent.registry;
using Xunit;

namespace agent.tests;

/// <summary>
/// v0.23.0 exp12 · S2 端到端接线机检 —— 节点执行前**必经**形式化闸门（挂在 `RunNodeAsync` 唯一前门上）。
/// 断言绑定**真实调度行为**，不是"函数被调用过"：
///  1) 被阻断的节点，其执行体**一次都不许被调用**（这是 token 层可观察的节省：节点没跑就没那次 LLM 调用）；
///  2) 节点终态必须是 Failed（阻断 ≠ 静默跳过，不得悄悄当成功）；
///  3) 输入级负向控制：同形节点**不带契约**必须照常执行 ⇒ 证明阻断由契约引起，而非调度器副作用；
///  4) 开关级负向控制：`AGENTFRAMEWORK_FORMAL_GATE=0` ⇒ 同一份被反驳契约也必须放行 ⇒ 证明"是闸门在阻断"。
/// </summary>
[Collection("formal-gate-env")]
public class PlanFormalGateWiringTests
{
    private const string RefutedContract = "premise x + y == 10\npremise x > 4\ngoal x < 100";
    private const string ProvedContract = "premise y >= 0\npremise x + y == 10\ngoal x <= 10";
    private const string FragmentContract = "premise x * x == 4\ngoal x == 2";

    private static PlanNode Node(string id, string? formal) => new()
    {
        Id = id,
        Text = "处理 $input",
        Intent = "general",
        Level = 0,
        Formal = formal,
    };

    private static TaskPlan Plan(params PlanNode[] nodes)
        => new() { PlanId = "s2-gate", Nodes = nodes.ToList(), MaxParallelism = 4 };

    private static TaskPlanExecutor Executor(List<string> order)
        => new(
            (n, ct) =>
            {
                lock (order) order.Add(n.Id);
                return Task.FromResult(new NodeExecutionResult
                {
                    NodeId = n.Id,
                    FinalState = PlanNodeState.Completed,
                    Output = $"out-{n.Id}",
                });
            },
            onWait: (n, producer, reason, ct) => Task.CompletedTask);

    [Fact]
    public void 被反驳的节点_执行体零调用且终态失败()
    {
        var order = new List<string>();
        var run = Executor(order).ExecuteAsync(Plan(Node("a", RefutedContract))).GetAwaiter().GetResult();

        Assert.Empty(order);                                                   // 执行体一次都没跑 ⇒ 没那次 LLM 调用
        Assert.Equal(PlanNodeState.Failed, run.NodeStates["a"]);               // 阻断不是"悄悄跳过"
    }

    [Fact]
    public void 已证节点_照常执行()
    {
        var order = new List<string>();
        var run = Executor(order).ExecuteAsync(Plan(Node("a", ProvedContract))).GetAwaiter().GetResult();

        Assert.Equal(["a"], order);
        Assert.Equal(PlanNodeState.Completed, run.NodeStates["a"]);
    }

    [Fact]
    public void 片段外契约_弃权阻断_不放行()
    {
        var order = new List<string>();
        var run = Executor(order).ExecuteAsync(Plan(Node("a", FragmentContract))).GetAwaiter().GetResult();

        Assert.Empty(order);
        Assert.Equal(PlanNodeState.Failed, run.NodeStates["a"]);
    }

    [Fact] // 输入级负向控制
    public void 无契约同形节点_照常执行()
    {
        var order = new List<string>();
        var run = Executor(order).ExecuteAsync(Plan(Node("a", null))).GetAwaiter().GetResult();

        Assert.Equal(["a"], order);
        Assert.Equal(PlanNodeState.Completed, run.NodeStates["a"]);
    }

    [Fact] // 开关级负向控制: 关掉闸门, 同一份被反驳契约必须放行
    public void 闸门关闭时_被反驳契约也放行()
    {
        var old = Environment.GetEnvironmentVariable(PlanNodeFormalGate.EnvSwitch);
        try
        {
            Environment.SetEnvironmentVariable(PlanNodeFormalGate.EnvSwitch, "0");
            var order = new List<string>();
            var run = Executor(order).ExecuteAsync(Plan(Node("a", RefutedContract))).GetAwaiter().GetResult();

            Assert.Equal(["a"], order);
            Assert.Equal(PlanNodeState.Completed, run.NodeStates["a"]);
        }
        finally
        {
            Environment.SetEnvironmentVariable(PlanNodeFormalGate.EnvSwitch, old);
        }
    }
}
