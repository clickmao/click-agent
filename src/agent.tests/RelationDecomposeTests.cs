using agent.intent;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.12 拆解优化: 连接词关系分级 — 顺序 (然后/接着) vs 并行 (同时/以及) vs 数据依赖 (基于/根据)。
/// 并行子任务必须落同一 ParallelGroup (同层), 顺序子任务保持执行链, 数据依赖仍然是硬依赖。
/// </summary>
public class RelationDecomposeTests
{
    [Fact]
    public void SequentialConnector_KeepsChain()
    {
        var tasks = IntentDecomposer.Decompose("先搜索资料，然后写总结");
        Assert.Equal(2, tasks.Count);
        Assert.Equal(IntentDecomposer.TaskRelation.Sequential, tasks[1].Relation); // 然后 → 顺序
    }

    [Fact]
    public void ParallelConnector_ProducesIndependentTasks()
    {
        var tasks = IntentDecomposer.Decompose("搜索AOT资料，同时写一首诗");
        Assert.Equal(2, tasks.Count);
        Assert.Equal(IntentDecomposer.TaskRelation.Parallel, tasks[1].Relation);   // 同时 → 并行
        Assert.False(tasks[1].DependsOnPrevious);
    }

    [Fact]
    public void DataDependency_StillHard()
    {
        // "然后基于结果写文档": "然后" 切分, 但子句以依赖词 "基于" 开头 → 数据依赖优先于顺序词
        var tasks = IntentDecomposer.Decompose("搜索资料，然后基于结果写文档");
        Assert.Equal(IntentDecomposer.TaskRelation.DependsOnOutput, tasks[1].Relation);
        Assert.True(tasks[1].DependsOnPrevious);

        var third = IntentDecomposer.Decompose("搜索资料，基于结果写文档");
        Assert.Equal(IntentDecomposer.TaskRelation.DependsOnOutput, third[1].Relation);
        Assert.True(third[1].DependsOnPrevious);
    }

    [Fact]
    public void ParallelTasks_SameParallelGroup_InPlan()
    {
        var plan = TaskPlanBuilder.Build("t", IntentDecomposer.Decompose("搜索AOT资料，同时写一首诗"));
        Assert.All(plan.Nodes, n => Assert.Empty(n.DependsOn));      // 无依赖
        Assert.Equal(0, plan.MaxLevel);                               // 同层
        Assert.Equal(plan.Nodes[0].Id, plan.ExecutableNodeIds[0]);    // 两个都立即可执行
        Assert.Equal(2, plan.ExecutableNodeIds.Count);
    }

    [Fact]
    public void MixedChain_ParallelThenSequential()
    {
        // 并行 + 顺序混合: "搜索A，同时写诗B，然后基于A写总结C"
        var tasks = IntentDecomposer.Decompose("搜索AOT资料，同时写一首诗，然后基于结果写总结");
        Assert.Equal(3, tasks.Count);
        Assert.Equal(IntentDecomposer.TaskRelation.Parallel, tasks[1].Relation);
        Assert.Equal(IntentDecomposer.TaskRelation.DependsOnOutput, tasks[2].Relation);
    }

    [Fact]
    public void ExistingV79Behaviors_Unchanged()
    {
        // v7.9 固化行为回归: 依赖标记/单句退化
        var single = IntentDecomposer.Decompose("帮我写个测试");
        Assert.Single(single);
        Assert.Equal(IntentDecomposer.TaskRelation.None, single[0].Relation);
    }
}
