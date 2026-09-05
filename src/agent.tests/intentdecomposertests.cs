using agent.core;
using agent.context;
using agent.intent;
using Xunit;

namespace agent.tests;

/// <summary>
/// 意图子任务拆解矩阵 (v7.9): 复合句切分 / 依赖标记 / 单句退化 / 数据源并集聚合。
/// 核心场景: "先搜索 X, 然后基于结果写个 Y" — 旧管线静默丢弃后半句。
/// </summary>
public class IntentDecomposerTests
{
    [Fact]
    public void CompoundSentence_SplitsIntoTwoSubTasks()
    {
        var tasks = IntentDecomposer.Decompose("先搜索 .NET 10 新特性，然后基于结果写个总结文档");

        Assert.Equal(2, tasks.Count);
        Assert.Equal(IntentRecognizer.Intents.Search, tasks[0].Intent);
        Assert.Equal(IntentRecognizer.Intents.CodeGeneration, tasks[1].Intent);
        Assert.True(tasks[1].DependsOnPrevious); // "基于结果" → 依赖前序
    }

    [Fact]
    public void CompoundSentence_WithoutDependencyMarker()
    {
        var tasks = IntentDecomposer.Decompose("搜索最新资讯，然后写一首诗");

        Assert.Equal(2, tasks.Count);
        Assert.False(tasks[1].DependsOnPrevious); // "写一首诗" 无依赖词
    }

    [Theory]
    [InlineData("审查这段代码，然后重构它", IntentRecognizer.Intents.CodeReview, IntentRecognizer.Intents.CodeModification)]
    [InlineData("列出文件，接着读取 appsettings.json", IntentRecognizer.Intents.FileOperation, IntentRecognizer.Intents.FileOperation)]
    [InlineData("git 提交，之后 push 到远端", IntentRecognizer.Intents.GitOperation, IntentRecognizer.Intents.GitOperation)]
    public void ConnectorVariants_SplitCorrectly(string input, string first, string second)
    {
        var tasks = IntentDecomposer.Decompose(input);
        Assert.Equal(2, tasks.Count);
        Assert.Equal(first, tasks[0].Intent);
        Assert.Equal(second, tasks[1].Intent);
    }

    [Fact]
    public void SingleIntentSentence_DegradesToSingleTask()
    {
        var tasks = IntentDecomposer.Decompose("帮我写一个 HTTP 客户端");

        Assert.Single(tasks);
        Assert.Equal(IntentRecognizer.Intents.CodeGeneration, tasks[0].Intent);
        Assert.False(tasks[0].DependsOnPrevious);
        Assert.Equal(0, tasks[0].Order);
    }

    [Fact]
    public void EmptyInput_ReturnsGeneralSingleTask()
    {
        var tasks = IntentDecomposer.Decompose("");
        Assert.Single(tasks);
        Assert.Equal(IntentRecognizer.Intents.General, tasks[0].Intent);
    }

    [Fact]
    public void FalseSplit_InsideWord_IsAvoided()
    {
        // "再次" 内含 "再", "先搜索" 内含 "先" — 不应在词内切开
        var tasks = IntentDecomposer.Decompose("请再次检查并搜索最新消息");

        Assert.Single(tasks); // 整句一个意图 (search), 不被 "再"/"先" 误切
        Assert.Equal(IntentRecognizer.Intents.Search, tasks[0].Intent);
    }

    [Fact]
    public void AggregateSources_UnionsAcrossSubTasks()
    {
        var tasks = IntentDecomposer.Decompose("搜索 .NET AOT 资料，然后写个示例项目");
        var sources = IntentDecomposer.AggregateSources(tasks);

        Assert.Contains(DataSourceType.WebSearch, sources);   // search 意图贡献
        Assert.Contains(DataSourceType.Memory, sources);      // 基础源
        Assert.Contains(DataSourceType.UserTendency, sources);
    }

    [Fact]
    public void PrimaryIntent_IsFirstSubTaskIntent()
    {
        var tasks = IntentDecomposer.Decompose("先审查代码，然后修改它");
        Assert.Equal(IntentRecognizer.Intents.CodeReview, IntentDecomposer.PrimaryIntent(tasks));
    }

    [Fact]
    public void ThreePartCompound_AllSeparated()
    {
        var tasks = IntentDecomposer.Decompose("搜索资料，然后写代码，最后写测试");

        Assert.Equal(3, tasks.Count);
        Assert.Equal(IntentRecognizer.Intents.Search, tasks[0].Intent);
        Assert.Equal(IntentRecognizer.Intents.CodeGeneration, tasks[1].Intent);
        Assert.Equal(IntentRecognizer.Intents.TestGeneration, tasks[2].Intent);
        Assert.Equal(0, tasks[0].Order);
        Assert.Equal(1, tasks[1].Order);
        Assert.Equal(2, tasks[2].Order);
    }
}
