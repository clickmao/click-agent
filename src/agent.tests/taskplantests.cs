using System.Text.Json;
using agent.core;
using agent.intent;
using agent.userinteraction;
using Xunit;
using Xunit.Abstractions;

namespace agent.tests;

/// <summary>
/// TaskPlan 图构建 + JSON 契约 + 插入指令分类 (v7.10)。
/// 覆盖: 依赖接线 / 问询节点生成 / 并行组判定 / JSON 往返 / 停止指令判定 / 敏感意图暂停。
/// </summary>
public class TaskPlanTests
{
    private readonly ITestOutputHelper _out;

    public TaskPlanTests(ITestOutputHelper output) => _out = output;

    [Fact]
    public void CompoundSentence_BuildsDependencyChain()
    {
        var subTasks = IntentDecomposer.Decompose("先搜索 .NET 10 新特性，然后基于结果写个总结文档");
        var plan = TaskPlanBuilder.Build("先搜索 .NET 10 新特性，然后基于结果写个总结文档", subTasks);

        Assert.Equal(2, plan.Nodes.Count);
        // "基于结果" → 第二节点依赖第一节点
        Assert.Equal(plan.Nodes[0].Id, plan.Nodes[1].DependsOn.Single());
        Assert.Equal(0, plan.Nodes[0].Level);
        Assert.Equal(1, plan.Nodes[1].Level);
        // 不同层 → 不同并行组 (不可并行)
        Assert.NotEqual(plan.Nodes[0].ParallelGroup, plan.Nodes[1].ParallelGroup);
    }

    [Fact]
    public void IndependentTasks_AreParallelizable()
    {
        // v7.12 语义: "同时" = Parallel → 无依赖接线, 同层并行组
        var subTasks = IntentDecomposer.Decompose("搜索 AOT 资料，同时写一首诗");
        var plan = TaskPlanBuilder.Build("测试", subTasks);

        Assert.All(plan.Nodes, n => Assert.Empty(n.DependsOn));
        Assert.Equal(0, plan.MaxLevel);
        Assert.Equal(plan.Nodes[0].ParallelGroup, plan.Nodes[1].ParallelGroup);
    }

    [Fact]
    public void SequentialConnector_ChainsDependency()
    {
        // v7.12 语义: "然后" = Sequential → 保执行序 (依赖接线), 层级递增
        var subTasks = IntentDecomposer.Decompose("搜索 AOT 资料，然后写一首诗");
        var plan = TaskPlanBuilder.Build("测试", subTasks);

        Assert.Empty(plan.Nodes[0].DependsOn);
        Assert.Single(plan.Nodes[1].DependsOn);
        Assert.Equal(plan.Nodes[0].Id, plan.Nodes[1].DependsOn[0]);
        Assert.Equal(1, plan.MaxLevel);
    }

    [Fact]
    public void MissingRequiredParameter_ProducesClarification_AndBlocksExecution()
    {
        // file_operation 意图必填 path → 问询节点; 其余节点不受影响
        var subTasks = IntentDecomposer.Decompose("读取文件");
        var plan = TaskPlanBuilder.Build("读取文件", subTasks);

        var node = plan.Nodes.Single();
        Assert.True(plan.HasPendingClarifications);
        Assert.False(node.IsExecutable);
        Assert.Empty(plan.ExecutableNodeIds);

        var clar = node.Clarifications.Single();
        Assert.Equal(ClarificationKinds.MissingParameter, clar.Kind);
        Assert.Equal("path", clar.ParameterName);
        Assert.Contains("子任务", clar.Question);       // 问询必须具体 (说明哪个子任务缺什么)
        Assert.Equal("MainAgentAllowed", clar.Authority);
    }

    [Fact]
    public void ClarificationAnswer_UnlocksNode_OnlyForThatNode()
    {
        var subTasks = IntentDecomposer.Decompose("读取文件，然后写一首诗");
        var plan = TaskPlanBuilder.Build("测试", subTasks);

        var fileNode = plan.Nodes.First(n => n.Intent == IntentRecognizer.Intents.FileOperation);
        var poemNode = plan.Nodes.First(n => n.Intent == IntentRecognizer.Intents.General);

        Assert.False(fileNode.IsExecutable);
        Assert.True(poemNode.IsExecutable);   // 参数无关的节点不联动阻塞

        TaskPlanBuilder.ApplyClarificationAnswer(plan, fileNode.Id, "path", "/tmp/data.json");
        Assert.True(fileNode.IsExecutable);
        Assert.Equal("/tmp/data.json", fileNode.Parameters.Single(p => p.Name == "path").Value);
        Assert.Equal([fileNode.Id, poemNode.Id], plan.ExecutableNodeIds);
    }

    [Fact]
    public void JsonContract_RoundTrips_WithLevelsAndGroups()
    {
        var subTasks = IntentDecomposer.Decompose("先搜索资料，然后基于结果写代码");
        var plan = TaskPlanBuilder.Build("测试", subTasks);
        plan.Nodes[1].Parameters.Add(new TaskParameter
        {
            Name = "language", DisplayName = "目标语言", IsRequired = false,
            SuggestedValues = ["csharp"],
        });

        var json = TaskPlanJsonContext.ToJson(plan);
        _out.WriteLine(json);

        // UI 消费契约: 合法 JSON + 关键字段齐全
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        Assert.True(root.TryGetProperty("Nodes", out var nodes));
        Assert.Equal(2, nodes.GetArrayLength());

        var first = nodes[0];
        Assert.True(first.TryGetProperty("Level", out _));
        Assert.True(first.TryGetProperty("ParallelGroup", out _));
        Assert.True(first.TryGetProperty("IsExecutable", out _));

        // 计算属性对 UI 有价值: 可执行节点高亮 + 等待澄清提示
        Assert.True(root.TryGetProperty("ExecutableNodeIds", out _));
        Assert.True(root.TryGetProperty("HasPendingClarifications", out _));

        // 问询条目结构
        var pendingPlan = TaskPlanBuilder.Build("读取文件", IntentDecomposer.Decompose("读取文件"));
        var json2 = TaskPlanJsonContext.ToJson(pendingPlan);
        using var doc2 = JsonDocument.Parse(json2);
        var clar = doc2.RootElement.GetProperty("Nodes")[0].GetProperty("Clarifications")[0];
        Assert.Equal("missing_parameter", clar.GetProperty("Kind").GetString());
        Assert.Equal("path", clar.GetProperty("ParameterName").GetString());
    }

    // ---------- 插入指令: 停止/审批/合并 ----------

    [Theory]
    [InlineData("停止", InjectedInstructionKind.Cancel)]
    [InlineData("先别做了，取消这个任务", InjectedInstructionKind.Cancel)]
    [InlineData("STOP", InjectedInstructionKind.Cancel)]
    [InlineData("android 是什么", InjectedInstructionKind.NewTask)]   // "cancel"⊂android 不误判
    [InlineData("之后要 push 前先问我", InjectedInstructionKind.RequestApproval)]
    [InlineData("补充一下，用 pnpm", InjectedInstructionKind.NewTask)]
    public void InjectedInstruction_Classification(string text, InjectedInstructionKind expected) =>
        Assert.Equal(expected, InjectedInstructionClassifier.Classify(text));

    [Fact]
    public void SensitiveIntents_RequireApproval()
    {
        Assert.True(InjectedInstructionClassifier.IsSensitiveIntent(IntentRecognizer.Intents.FileOperation));
        Assert.True(InjectedInstructionClassifier.IsSensitiveIntent(IntentRecognizer.Intents.GitOperation));
        Assert.False(InjectedInstructionClassifier.IsSensitiveIntent(IntentRecognizer.Intents.Search));
    }

    [Fact]
    public void MergeInstruction_AppendsNode_WithDependency()
    {
        var plan = TaskPlanBuilder.Build("t", IntentDecomposer.Decompose("写个文档"));
        var before = plan.Nodes.Count;

        var merged = TaskPlanBuilder.MergeInstruction(plan, "然后基于它写测试", plan.Nodes[^1].Id);

        Assert.Equal(before + 1, plan.Nodes.Count);
        Assert.Equal(IntentRecognizer.Intents.TestGeneration, merged.Intent);
        Assert.Equal(plan.Nodes[0].Id, merged.DependsOn.Single());   // 依赖原尾节点
        Assert.Equal(1, merged.Level);
    }
}
