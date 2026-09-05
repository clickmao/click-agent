using agent.core;
using agent.context;
using agent.intent;
using Xunit;

namespace agent.tests;

/// <summary>
/// 意图→数据源映射矩阵 (v7.6): 每种意图必须启用正确的召回源。
/// 错误映射的直接后果: search 意图没网搜 → 答案过时; code_generation 带网搜 → 浪费 token 与延迟。
/// </summary>
public class IntentSourceMappingTests
{
    [Theory]
    [InlineData(IntentRecognizer.Intents.Search)]
    [InlineData(IntentRecognizer.Intents.General)]
    public void InfoSeekingIntents_EnableWebSearch(string intent)
    {
        var sources = IntentSourceMapping.GetSources(intent);
        Assert.Contains(DataSourceType.WebSearch, sources);
        Assert.True(IntentSourceMapping.NeedsWebSearch(intent));
    }

    [Theory]
    [InlineData(IntentRecognizer.Intents.CodeGeneration)]
    [InlineData(IntentRecognizer.Intents.CodeModification)]
    [InlineData(IntentRecognizer.Intents.CodeReview)]
    [InlineData(IntentRecognizer.Intents.TestGeneration)]
    [InlineData(IntentRecognizer.Intents.FileOperation)]
    [InlineData(IntentRecognizer.Intents.GitOperation)]
    [InlineData(IntentRecognizer.Intents.MemorySearch)]
    public void CodeAndToolIntents_DisableWebSearch(string intent)
    {
        var sources = IntentSourceMapping.GetSources(intent);
        Assert.DoesNotContain(DataSourceType.WebSearch, sources);
        Assert.False(IntentSourceMapping.NeedsWebSearch(intent));
    }

    [Theory]
    [InlineData(IntentRecognizer.Intents.Search)]
    [InlineData(IntentRecognizer.Intents.CodeGeneration)]
    [InlineData(IntentRecognizer.Intents.MemorySearch)]
    [InlineData(IntentRecognizer.Intents.General)]
    public void AllIntents_AlwaysIncludeBaseSources(string intent)
    {
        var sources = IntentSourceMapping.GetSources(intent);
        Assert.Contains(DataSourceType.Memory, sources);
        Assert.Contains(DataSourceType.UserTendency, sources);
    }

    [Fact]
    public void UnknownIntent_FallsBackToGeneralSources()
    {
        // 未知意图按 general 处理 (兜底策略: 保守启用网搜)
        var sources = IntentSourceMapping.GetSources("nonexistent_intent");
        Assert.Contains(DataSourceType.WebSearch, sources);
    }

    [Fact]
    public void GetSources_ReturnsIndependentSets()
    {
        // 两次调用返回独立集合 — 防止共享可变状态跨请求污染
        var a = IntentSourceMapping.GetSources(IntentRecognizer.Intents.Search);
        var b = IntentSourceMapping.GetSources(IntentRecognizer.Intents.CodeGeneration);
        Assert.NotSame(a, b);
        Assert.DoesNotContain(DataSourceType.WebSearch, b);
    }
}
