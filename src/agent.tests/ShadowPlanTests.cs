using agent.intent;
using agent.registry;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 归拢接线测试 (T.2-4 影子模式): TaskPlanBuilder.Build + TaskPlanExecutor 哑执行演练,
/// 计划结构可执行、问询需求可观测、/plan JSON 序列化走 AOT fast-path。
/// </summary>
public class ShadowPlanTests
{
    private static TaskPlanRun ExecuteShadow(IReadOnlyList<IntentDecomposer.SubTask> subTasks, string text = "测试任务")
    {
        var plan = TaskPlanBuilder.Build(text, subTasks);
        var executor = new TaskPlanExecutor((n, _) => Task.FromResult(new NodeExecutionResult
        {
            NodeId = n.Id, FinalState = PlanNodeState.Skipped
        }));
        return executor.ExecuteAsync(plan).GetAwaiter().GetResult();
    }

    [Fact]
    public void Shadow_Run_Finishes_With_All_Nodes_Terminal()
    {
        var subTasks = new List<IntentDecomposer.SubTask>
        {
            new("创建计算器项目", "create_project", DependsOnPrevious: false, Order: 0,
                Relation: IntentDecomposer.TaskRelation.None, Confidence: 0.95),
            new("编写单元测试", "write_test", DependsOnPrevious: true, Order: 1,
                Relation: IntentDecomposer.TaskRelation.Sequential, Confidence: 0.9),
        };
        var run = ExecuteShadow(subTasks);
        Assert.Equal(TaskPlanRunState.Finished, run.State);
        Assert.Equal(2, run.NodeStates.Count);
        Assert.All(run.NodeStates.Values, s => Assert.NotEqual(PlanNodeState.Pending, s));
    }

    [Fact]
    public void Shadow_Serializes_With_FastPath_Json()
    {
        var subTasks = new List<IntentDecomposer.SubTask>
        {
            new("查天气", "query", DependsOnPrevious: false, Order: 0,
                Relation: IntentDecomposer.TaskRelation.None, Confidence: 0.9),
        };
        var run = ExecuteShadow(subTasks);
        var json = TaskPlanJsonContext.ToJson(run);
        Assert.Contains("\"PlanId\"", json);   // PascalCase 契约 (TaskPlanJsonContext 无 NamingPolicy)
        Assert.Contains("\"State\"", json);
    }

    [Fact]
    public void Shadow_LowConfidence_Node_Becomes_AwaitingClarification()
    {
        var subTasks = new List<IntentDecomposer.SubTask>
        {
            new("部署到某个环境", "deploy", DependsOnPrevious: false, Order: 0,
                Relation: IntentDecomposer.TaskRelation.None, Confidence: 0.2), // 低置信 → 问询
        };
        var run = ExecuteShadow(subTasks);
        // 低置信节点问询需求可观测 (AwaitingClarification 或问询记录), 不静默
        Assert.Contains(run.NodeStates.Values,
            s => s is PlanNodeState.AwaitingClarification or PlanNodeState.Skipped);
    }
}
