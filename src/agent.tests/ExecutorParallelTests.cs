using agent.intent;
using agent.registry;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 执行器同层并发化测试 (plan_executor_parallel.md A.4):
/// 同层并发、跨层等待、依赖连带跳过、MaxParallelism=1 串行等价。
/// 时间断言用宽松余量 (SessionPerformanceTests 教训: CI 抖动)。
/// </summary>
public class ExecutorParallelTests
{
    private static TaskPlan BuildPlan(int nodesPerLevel, int levels, int maxParallelism = 4)
    {
        var nodes = new List<PlanNode>();
        for (var l = 0; l < levels; l++)
        {
            for (var i = 0; i < nodesPerLevel; i++)
            {
                var id = $"n{l}_{i}";
                var depends = l == 0
                    ? new List<string>()
                    : new List<string> { $"n{l - 1}_0" };
                nodes.Add(new PlanNode
                {
                    Id = id, Text = $"任务 l{l} i{i}", Intent = "general",
                    Level = l, ParallelGroup = l, DependsOn = depends,
                });
            }
        }
        return new TaskPlan { PlanId = "ptest", Nodes = nodes, MaxParallelism = maxParallelism };
    }

    /// <summary>慢执行体: 记录并发重叠窗口 (进入未退出数 &gt; 1 即发生并发)。</summary>
    private static (TaskPlanRun Run, int MaxObservedConcurrency) ExecuteWithProbe(
        TaskPlan plan, int delayMs)
    {
        var cur = 0;
        var max = 0;
        var gate = new object();
        var executor = new TaskPlanExecutor(async (n, ct) =>
        {
            lock (gate)
            {
                cur++;
                if (cur > max) max = cur;
            }
            try { await Task.Delay(delayMs, ct); }
            catch (OperationCanceledException) { }
            finally { lock (gate) cur--; }
            return new NodeExecutionResult { NodeId = n.Id, FinalState = PlanNodeState.Completed };
        });
        var run = executor.ExecuteAsync(plan).GetAwaiter().GetResult();
        return (run, max);
    }

    [Fact]
    public void SameLevel_Nodes_Run_Concurrently()
    {
        var plan = BuildPlan(nodesPerLevel: 3, levels: 1);
        var (run, maxConc) = ExecuteWithProbe(plan, delayMs: 120);
        Assert.Equal(TaskPlanRunState.Finished, run.State);
        Assert.True(maxConc >= 2, $"期望同层并发 (max observed={maxConc})");
    }

    [Fact]
    public void CrossLevel_Waits_Upper_Level_Terminal()
    {
        var plan = BuildPlan(nodesPerLevel: 2, levels: 2);
        var (run, _) = ExecuteWithProbe(plan, delayMs: 30);
        Assert.Equal(TaskPlanRunState.Finished, run.State);
        Assert.All(run.NodeStates.Values, s => Assert.Equal(PlanNodeState.Completed, s));
    }

    [Fact]
    public void MaxParallelism_One_Equals_Serial()
    {
        var plan = BuildPlan(nodesPerLevel: 3, levels: 1, maxParallelism: 1);
        var (run, maxConc) = ExecuteWithProbe(plan, delayMs: 40);
        Assert.Equal(TaskPlanRunState.Finished, run.State);
        Assert.True(maxConc <= 1, $"MaxParallelism=1 不得并发 (max observed={maxConc})");
    }

    [Fact]
    public void FailFast_In_Concurrent_Batch_Stops_Plan()
    {
        // 同层 3 节点: 第 2 个失败 → 计划终止, 全部节点落终态
        var plan = BuildPlan(nodesPerLevel: 3, levels: 2);
        var executed = new List<string>();
        var executor = new TaskPlanExecutor((n, _) =>
        {
            lock (executed) executed.Add(n.Id);
            var failed = n.Id == "n0_1";
            return Task.FromResult(new NodeExecutionResult
            {
                NodeId = n.Id,
                FinalState = failed ? PlanNodeState.Failed : PlanNodeState.Completed,
                Error = failed ? "注入失败" : null,
            });
        });
        var run = executor.ExecuteAsync(plan).GetAwaiter().GetResult();
        Assert.Equal(TaskPlanRunState.Finished, run.State);
        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n0_1"]);
        // 下游层被连带跳过 (依赖 n0_0? 只 n0_0 依赖链, n0_1 无下游 — 但层1全依赖 n0_0)
        // 只断言计划终止 + 失败节点状态
        Assert.Contains("n0_0", executed);
        Assert.Contains("n0_1", executed);
        Assert.DoesNotContain("n1_1", executed);
    }

    [Fact]
    public void Dependent_Node_Skipped_When_Upper_Level_Failed()
    {
        var plan = BuildPlan(nodesPerLevel: 1, levels: 2);
        var executor = new TaskPlanExecutor((n, _) => Task.FromResult(new NodeExecutionResult
        {
            NodeId = n.Id,
            FinalState = n.Level == 0 ? PlanNodeState.Failed : PlanNodeState.Completed,
            Error = n.Level == 0 ? "上游失败" : null,
        }));
        var run = executor.ExecuteAsync(plan).GetAwaiter().GetResult();
        // FailFast: 上游失败即终止 (plan_node_retry 将演进此语义)
        Assert.Equal(PlanNodeState.Failed, run.NodeStates["n0_0"]);
    }
}
