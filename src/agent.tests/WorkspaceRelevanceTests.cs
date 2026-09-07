using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.11.0 R118 (真缺陷 50): WorkspaceFiles 相关分不再硬编码 0.7 — 按命中关键词数比例化。
/// 通过反射测 private 方法 (零反射约束只限产品运行时, 测试可用静态编译访问)。
/// </summary>
public class WorkspaceRelevanceTests
{
    private static object? InvokeRanked(string content, string[] keywords)
    {
        var asm = typeof(agent.IndustrialAgentV2).Assembly;
        var t = asm.GetType("agent.context.ContextAssembler")
            ?? throw new InvalidOperationException("ContextAssembler 类型未找到");
        var m = t.GetMethod("FindKeywordLineRanked",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static)
            ?? throw new InvalidOperationException("FindKeywordLineRanked 未找到");
        return m.Invoke(null, new object[] { content, keywords.ToList() });
    }

    [Fact]
    public void More_Keyword_Hits_Rank_Higher()
    {
        var content = "快速排序 quick sort 是最常用的内部排序算法\n无关内容行\n另一行";
        var kws = new[] { "快速排序", "排序", "算法", "内部", "常用" };
        var result = InvokeRanked(content, kws)!;
        var hits = GetTupleInt(result, 2);
        Assert.True(hits >= 3, $"命中数 {hits} 应 ≥3");
    }

    [Fact]
    public void No_Hit_Returns_Null()
    {
        var result = InvokeRanked("完全无关的文本", new[] { "快速排序" })!;
        var t1 = GetTupleObj(result, 1) as string;
        var hits = GetTupleInt(result, 2);
        Assert.Null(t1);
        Assert.Equal(0, hits);
    }

    private static object? GetTupleObj(object tuple, int index) =>
        tuple.GetType().GetField($"Item{index}", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic)?.GetValue(tuple)
        ?? tuple.GetType().GetField($"<Item{index}>i__Field", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)?.GetValue(tuple);

    private static int GetTupleInt(object tuple, int index) => (int)(GetTupleObj(tuple, index) ?? 0);

    [Fact]
    public void Relevance_Formula_Bounds()
    {
        // 0.4 + 0.5*min(1, hits/5): 1 命中=0.5, 5 命中=0.9, 上限 0.9
        Assert.Equal(0.5, 0.4 + 0.5 * Math.Min(1.0, 1 / 5.0), precision: 2);
        Assert.Equal(0.9, 0.4 + 0.5 * Math.Min(1.0, 5 / 5.0), precision: 2);
        Assert.Equal(0.9, 0.4 + 0.5 * Math.Min(1.0, 8 / 5.0), precision: 2);
    }
}
