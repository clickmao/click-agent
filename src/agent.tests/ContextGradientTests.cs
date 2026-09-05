using agent.contextgradient;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 上下文梯度压缩测试 (plan_context_compression.md P1 规则版验收):
/// 四级梯度分配、锚词防漂移回退、规则压缩去重、标题截断。
/// </summary>
public class ContextGradientTests
{
    private const string LongText =
        "AgentFramework 是一个工业级智能体框架。它支持意图识别与多源上下文组装。语境压缩是核心能力之一。" +
        "任务计划支持并行执行。AgentFramework 的目标是可审计与可扩展。" +
        "上下文梯度压缩按相关性分级。TaskPlan 图调度支持同层并发。";

    [Fact]
    public void High_Relevance_Keeps_Full_Text()
    {
        var compressor = new ContextGradientCompressor();
        var result = compressor.Compress(new GradientRequest
        {
            Content = LongText, RelevanceScore = 0.9, AnchorWords = { "AgentFramework" },
        });
        Assert.Equal(GradientLevel.Full, result.Level);
        Assert.Equal(LongText, result.Content);
        Assert.True(result.DriftCheckPassed);
    }

    [Fact]
    public void Mid_Relevance_Takes_Sentences()
    {
        var compressor = new ContextGradientCompressor();
        var result = compressor.Compress(new GradientRequest
        {
            Content = LongText, RelevanceScore = 0.6,
        });
        Assert.Equal(GradientLevel.SummarySentences, result.Level);
        Assert.True(result.CompressedChars < result.OriginalChars);
        Assert.StartsWith("AgentFramework", result.Content); // 首句保留
    }

    [Fact]
    public void Low_Relevance_Rule_Compresses()
    {
        var compressor = new ContextGradientCompressor();
        var result = compressor.Compress(new GradientRequest
        {
            Content = LongText + "\n重复行\n重复行\n", RelevanceScore = 0.4, TokenBudget = 60,
        });
        Assert.Equal(GradientLevel.RuleCompressed, result.Level);
        Assert.DoesNotContain("重复行\n重复行", result.Content); // 重复行去重
        Assert.True(result.CompressedChars <= result.OriginalChars);
    }

    [Fact]
    public void Minimal_Relevance_Title_Only()
    {
        var compressor = new ContextGradientCompressor();
        var result = compressor.Compress(new GradientRequest
        {
            Content = LongText, RelevanceScore = 0.1,
        });
        Assert.Equal(GradientLevel.TitleOnly, result.Level);
        Assert.True(result.Content.Length <= 81); // ≤80 字符 + 省略号
    }

    [Fact]
    public void Drift_Anchor_Missing_Falls_Back_To_Full()
    {
        var compressor = new ContextGradientCompressor();
        // 锚词 "区块链" 只在结尾 — 摘句版 (前 4 句) 丢锚 → 回退全文
        var text = "第一句无关内容。第二句也无关。第三句还是无关。第四句结束了。结尾提到区块链。";
        var result = compressor.Compress(new GradientRequest
        {
            Content = text, RelevanceScore = 0.6, AnchorWords = { "区块链" },
        });
        Assert.Equal(GradientLevel.Full, result.Level); // 回退
        Assert.True(result.DriftCheckPassed);
        Assert.Contains("区块链", result.Content);
    }

    [Fact]
    public void No_Anchor_Always_Passes()
    {
        var compressor = new ContextGradientCompressor();
        var result = compressor.Compress(new GradientRequest
        {
            Content = LongText, RelevanceScore = 0.1, AnchorWords = { },
        });
        Assert.True(result.DriftCheckPassed);
    }

    [Fact]
    public void Levels_Are_Monotonic_By_Relevance()
    {
        var compressor = new ContextGradientCompressor();
        double[] scores = { 0.9, 0.6, 0.4, 0.1 };
        GradientLevel[] expected =
        {
            GradientLevel.Full, GradientLevel.SummarySentences,
            GradientLevel.RuleCompressed, GradientLevel.TitleOnly,
        };
        for (var i = 0; i < scores.Length; i++)
        {
            var r = compressor.Compress(new GradientRequest { Content = LongText, RelevanceScore = scores[i] });
            Assert.Equal(expected[i], r.Level);
        }
    }
}
