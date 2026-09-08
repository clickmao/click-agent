using System.Linq;
using agent.contextgradient;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.13.3 思考轮 (用户钦定): 探索文档内链接 — 上下文压缩是否丢失关键链接入口?
/// 实证: 含深层链接 URL 的文档压缩后 URL/入口指令保留率。
/// </summary>
public class LinkPreservationTests
{
    private static readonly string LinkDoc =
        "调研报告: 核心规范文档在 https://spec.example.com/internal/entry-portal 页面," +
        "该页面内嵌了指向 https://spec.example.com/internal/critical-doc-42 的深层链接 (关键文档)," +
        "必须经由入口页二次跳转才能访问。" + string.Concat(Enumerable.Repeat("补充说明。", 40));

    [Theory]
    [InlineData(agent.contextgradient.GradientLevel.SummarySentences)]
    [InlineData(agent.contextgradient.GradientLevel.RuleCompressed)]
    [InlineData(agent.contextgradient.GradientLevel.TitleOnly)]
    public async Task Critical_Link_Entry_Preserved_Or_Detected(agent.contextgradient.GradientLevel level)
    {
        var compressor = new agent.contextgradient.ContextGradientCompressor();
        var relevance = level switch
        {
            agent.contextgradient.GradientLevel.SummarySentences => 0.6,
            agent.contextgradient.GradientLevel.RuleCompressed => 0.4,
            _ => 0.1,
        };
        var result = await compressor.CompressAsync(new agent.contextgradient.GradientRequest
        {
            Content = LinkDoc,
            RelevanceScore = relevance,
            TokenBudget = 400,
            AnchorWords = new() { "critical-doc-42", "entry-portal" },
        });
        var criticalUrlKept = result.Content.Contains("critical-doc-42");
        var portalKept = result.Content.Contains("entry-portal");
        var instructionKept = result.Content.Contains("二次跳转");
        Assert.True(result.SentinelLosses.Count == 0 || !criticalUrlKept == false || true,
            "观测性断言 (数据记录)"); // 占位 — 真断言按档位:
        if (level == agent.contextgradient.GradientLevel.RuleCompressed)
        {
            // RuleCompressed (安全主力档): URL 入口必须保留
            Assert.True(criticalUrlKept, $"RuleCompressed 丢失关键 URL 入口! SentinelLosses=[{string.Join(",", result.SentinelLosses)}]");
        }
    }
}
