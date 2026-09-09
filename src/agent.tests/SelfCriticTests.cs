using agent.critique;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.14.0 T2a SelfCritic 单测: 契约 + 逐字子串防幻觉锚 (R149 真断言标准)。
/// </summary>
public class SelfCriticTests
{
    private const string Output = """
        foreach (var input in new[] { a.In0, a.In1 })
        {
            var x = g.Resolve(input);
        }
        """;

    [Fact]
    public void Parse_ValidCritique_Kept()
    {
        var reply = """[{"quote":"new[] { a.In0, a.In1 }","mechanism":"每次迭代堆分配数组","severity":"high","fix_hint":"ref 局部变量"}]""";
        var r = SelfCritic.Parse(reply, Output);
        Assert.Single(r.Valid);
        Assert.Equal(0, r.Rejected);
        Assert.Contains("堆分配", r.Valid[0].Mechanism);
    }

    [Fact]
    public void Parse_HallucinatedQuote_Rejected()
    {
        // quote 不在原文中 (幻觉锚) — 必须拒
        var reply = """[{"quote":"new Dictionary<string,int>()","mechanism":"编造的机制","severity":"high","fix_hint":"x"}]""";
        var r = SelfCritic.Parse(reply, Output);
        Assert.Empty(r.Valid);
        Assert.Equal(1, r.Rejected);
    }

    [Fact]
    public void Parse_MissingMechanism_Rejected()
    {
        var reply = """[{"quote":"new[]","mechanism":"","severity":"high","fix_hint":""}]""";
        var r = SelfCritic.Parse(reply, Output);
        Assert.Empty(r.Valid);
        Assert.Equal(1, r.Rejected);
    }

    [Fact]
    public void Parse_NonJson_ReturnsEmpty()
    {
        var r = SelfCritic.Parse("我没有发现问题。", Output);
        Assert.Empty(r.Valid);
    }

    [Fact]
    public void Parse_MalformedJsonArray_Tolerated()
    {
        var r = SelfCritic.Parse("[{quote:broken}]", Output);
        Assert.Empty(r.Valid);
    }

    [Fact]
    public void Parse_Mixed_OneValidOneHallucinated()
    {
        var reply = """[{"quote":"new[] { a.In0, a.In1 }","mechanism":"堆分配","severity":"high","fix_hint":"ref"},{"quote":"不存在的代码片段","mechanism":"幻觉","severity":"low","fix_hint":""}]""";
        var r = SelfCritic.Parse(reply, Output);
        Assert.Single(r.Valid);
        Assert.Equal(1, r.Rejected);
    }

    [Fact]
    public void BuildPrompt_ContainsChecklistAndOutput()
    {
        var p = SelfCritic.BuildPrompt(Output, "C#", new[] { "R01 堆分配", "R03 async void" });
        Assert.Contains(Output, p);
        Assert.Contains("R01 堆分配", p);
        Assert.Contains("逐字子串", p);
        Assert.Contains("机制解释", p);
    }
}
