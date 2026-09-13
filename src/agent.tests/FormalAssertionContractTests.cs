using Xunit;
using agent.registry;

namespace agent.tests;

/// <summary>
/// v0.23.0-exp12 · S1(M4) 形式化断言契约单测。
/// 覆盖四条铁律: 缺失≠错误 / 显式 no_formal / 残缺不放行 / 任何分支不触发 LLM 追问。
/// 含负向控制(自相矛盾、裸关键字、自然语言散文不得被误判为断言)。
/// </summary>
public sealed class FormalAssertionContractTests
{
    // ── 铁律 1: 缺失 ≠ 错误(不要求 LLM 返回形式化数据) ──────────────────

    [Fact]
    public void Null_IsNoFormal_Absent_AndPassable()
    {
        var r = FormalAssertionContract.Parse(null);
        Assert.Equal(FormalContractDecision.NoFormal, r.Decision);
        Assert.Equal("absent", r.ReasonCode);
        Assert.True(r.IsPassable);
        Assert.False(r.NeedsKernel);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("\n\t\n")]
    public void Blank_IsNoFormal_Absent(string text)
    {
        var r = FormalAssertionContract.Parse(text);
        Assert.Equal(FormalContractDecision.NoFormal, r.Decision);
        Assert.Equal("absent", r.ReasonCode);
        Assert.True(r.IsPassable);
    }

    [Fact]
    public void NaturalLanguageProse_IsNotMisclassifiedAsAssertion()
    {
        const string prose = "帮我把这个仓库的 CI 跑通, 注意不要动产品代码。\n先看 workflow 文件。";
        var r = FormalAssertionContract.Parse(prose);
        Assert.Equal(FormalContractDecision.NoFormal, r.Decision);
        Assert.Equal("absent", r.ReasonCode);
        Assert.True(r.IsPassable);
    }

    // ── 铁律 2: 显式声明 no_formal ────────────────────────────────────

    [Fact]
    public void ExplicitNoFormal_WithReason_IsDeclared()
    {
        var r = FormalAssertionContract.Parse("no_formal: 该节点只做资源下载, 无可判定片段");
        Assert.Equal(FormalContractDecision.NoFormal, r.Decision);
        Assert.Equal("declared", r.ReasonCode);
        Assert.Equal("该节点只做资源下载, 无可判定片段", r.Declaration);
        Assert.True(r.IsPassable);
    }

    [Theory]
    [InlineData("NO_FORMAL")]
    [InlineData("No_Formal: 大写兼容")]
    public void NoFormalMarker_IsCaseInsensitive(string text)
    {
        var r = FormalAssertionContract.Parse(text);
        Assert.Equal(FormalContractDecision.NoFormal, r.Decision);
        Assert.Equal("declared", r.ReasonCode);
    }

    // ── 铁律 3: 齐备断言 ⇒ 交内核 ─────────────────────────────────────

    [Fact]
    public void CompleteAssertion_IsHandedToKernel()
    {
        const string text = "# 可判定片段\npremise x + y == 10\npremise x > 4\n\ngoal x < 100";
        var r = FormalAssertionContract.Parse(text);
        Assert.Equal(FormalContractDecision.Assertion, r.Decision);
        Assert.Equal("assertion", r.ReasonCode);
        Assert.True(r.NeedsKernel);
        Assert.False(r.IsPassable);
        Assert.Equal("premise x + y == 10\npremise x > 4\ngoal x < 100", r.AssertionText);
        Assert.Equal(r.AssertionText, FormalAssertionContract.ToKernelAssertText(r));
    }

    [Fact]
    public void MultipleGoals_ArePreserved()
    {
        var r = FormalAssertionContract.Parse("premise x >= 0\ngoal x <= 10\ngoal x != 3");
        Assert.Equal(FormalContractDecision.Assertion, r.Decision);
        Assert.Contains("goal x != 3", r.AssertionText);
    }

    // ── 铁律 3 负向控制: 残缺/矛盾 ⇒ Malformed, 不放行 ─────────────────

    [Fact]
    public void PremiseOnly_IsMalformed_Incomplete()
    {
        var r = FormalAssertionContract.Parse("premise x > 4");
        Assert.Equal(FormalContractDecision.Malformed, r.Decision);
        Assert.Equal("incomplete", r.ReasonCode);
        Assert.False(r.IsPassable);
        Assert.False(r.NeedsKernel);
    }

    [Fact]
    public void GoalOnly_IsMalformed_Incomplete()
    {
        var r = FormalAssertionContract.Parse("goal x < 100");
        Assert.Equal(FormalContractDecision.Malformed, r.Decision);
        Assert.Equal("incomplete", r.ReasonCode);
    }

    [Fact]
    public void BareKeyword_IsMalformed()
    {
        var r = FormalAssertionContract.Parse("premise\ngoal x < 1");
        Assert.Equal(FormalContractDecision.Malformed, r.Decision);
        Assert.Equal("incomplete", r.ReasonCode);
    }

    [Fact]
    public void NoFormalTogetherWithAssertion_IsMalformed_Conflict()
    {
        var r = FormalAssertionContract.Parse("no_formal: 懒得写\npremise x > 4\ngoal x < 10");
        Assert.Equal(FormalContractDecision.Malformed, r.Decision);
        Assert.Equal("no_formal_with_assertion", r.ReasonCode);
        Assert.False(r.IsPassable);
    }

    [Fact]
    public void KeywordMustBeWholeWord()
    {
        // "premises are ..." 不是断言行 —— 不得被误判
        var r = FormalAssertionContract.Parse("premises are the following\nnothing else");
        Assert.Equal(FormalContractDecision.NoFormal, r.Decision);
        Assert.Equal("absent", r.ReasonCode);
    }

    // ── 铁律 5: 任何分支都不得要求 LLM 重试 ────────────────────────────

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("no_formal: x")]
    [InlineData("premise x > 4\ngoal x < 10")]
    [InlineData("premise x > 4")]
    [InlineData("no_formal: y\npremise x > 4\ngoal x < 10")]
    public void NeverRequiresLlmRetry(string? text)
    {
        var r = FormalAssertionContract.Parse(text);
        Assert.False(r.RequiresLlmRetry);
    }
}
