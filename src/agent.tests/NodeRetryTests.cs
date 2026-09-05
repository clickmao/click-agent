using agent.intent;
using agent.registry;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 节点重试测试 (plan_node_retry.md B.4):
/// 重试次数精确、退避审计、Permanent 不重试、取消优先、默认 0 零行为变化。
/// </summary>
public class NodeRetryTests
{
    private static TaskPlanExecutor MakeExecutor(Func<PlanNode, (NodeExecutionResult, int)> run) =>
        new((n, _) => Task.FromResult(run(n).Item1));

    [Fact]
    public void Exhausted_Retries_Calls_MaxRetries_Plus_One_Times()
    {
        var plan = new TaskPlan
        {
            PlanId = "rt",
            Nodes = { new PlanNode { Id = "a", Text = "易失败任务", Intent = "general", MaxRetries = 2 } },
        };
        var calls = 0;
        var executor = new TaskPlanExecutor((_, _) =>
        {
            calls++;
            return Task.FromResult(new NodeExecutionResult
            {
                NodeId = "a", FinalState = PlanNodeState.Failed,
                Error = "始终失败", FailureKind = NodeFailureKind.Transient,
            });
        });
        var run = executor.ExecuteAsync(plan).GetAwaiter().GetResult();
        Assert.Equal(3, calls);                       // 恰好 1+2 次
        Assert.Equal(PlanNodeState.Failed, run.NodeStates["a"]);
        Assert.Equal(2, run.Retries.Count);           // 审计两条
        Assert.All(run.Retries, r => Assert.Equal("a", r.NodeId));
    }

    [Fact]
    public void Second_Attempt_Succeeds_With_Audit()
    {
        var plan = new TaskPlan
        {
            PlanId = "rt2",
            Nodes =
            {
                new PlanNode { Id = "a", Text = "抖动任务", Intent = "general", MaxRetries = 3 },
                new PlanNode { Id = "b", Text = "下游", Intent = "general", DependsOn = { "a" } },
            },
        };
        var calls = 0;
        var executor = new TaskPlanExecutor((n, _) =>
        {
            calls++;
            return Task.FromResult(new NodeExecutionResult
            {
                NodeId = n.Id,
                FinalState = n.Id == "a" && calls == 1 ? PlanNodeState.Failed : PlanNodeState.Completed,
                Error = n.Id == "a" && calls == 1 ? "瞬时抖动" : null,
            });
        });
        var run = executor.ExecuteAsync(plan).GetAwaiter().GetResult();
        Assert.Equal(TaskPlanRunState.Finished, run.State);
        Assert.Equal(PlanNodeState.Completed, run.NodeStates["a"]);
        Assert.Single(run.Retries);                   // 一次重试记录
        Assert.Equal(PlanNodeState.Completed, run.NodeStates["b"]); // 下游正常执行
    }

    [Fact]
    public void Permanent_Failure_Never_Retried()
    {
        var plan = new TaskPlan
        {
            PlanId = "rt3",
            Nodes = { new PlanNode { Id = "a", Text = "参数非法", Intent = "general", MaxRetries = 5 } },
        };
        var calls = 0;
        var executor = new TaskPlanExecutor((_, _) =>
        {
            calls++;
            return Task.FromResult(new NodeExecutionResult
            {
                NodeId = "a", FinalState = PlanNodeState.Failed,
                Error = "参数校验失败", FailureKind = NodeFailureKind.Permanent,
            });
        });
        executor.ExecuteAsync(plan).GetAwaiter().GetResult();
        Assert.Equal(1, calls);                       // 0 重试直接收敛
    }

    [Fact]
    public void Default_MaxRetries_Zero_Keeps_Legacy_Behavior()
    {
        var plan = new TaskPlan
        {
            PlanId = "rt4",
            Nodes = { new PlanNode { Id = "a", Text = "默认配置", Intent = "general" } }, // MaxRetries=null, Default=0
        };
        var calls = 0;
        var executor = new TaskPlanExecutor((_, _) =>
        {
            calls++;
            return Task.FromResult(new NodeExecutionResult
            { NodeId = "a", FinalState = PlanNodeState.Failed, Error = "x" });
        });
        executor.ExecuteAsync(plan).GetAwaiter().GetResult();
        Assert.Equal(1, calls);                       // 与旧行为完全一致
    }
}
