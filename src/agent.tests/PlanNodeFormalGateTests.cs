using Xunit;
using agent.intent;

namespace agent.tests;

/// <summary>
/// v0.23.0-exp12 · S2 节点级形式化闸门单测。
/// 语义表逐条可证伪: 未声明⇒放行 / 显式弃权⇒放行 / 已证⇒放行 / 反驳⇒阻断+反例 /
/// 空真⇒阻断 / 片段外⇒弃权(Abstained, 不计违规) / 畸形⇒阻断。并断言"任何分支都不产生 LLM 调用"。
/// </summary>
[Collection("formal-gate-env")]   // 与 PlanFormalGateWiringTests 串行: 两者都会读写 AGENTFRAMEWORK_FORMAL_GATE, 并行会互相污染
public sealed class PlanNodeFormalGateTests
{
    private const string ProvedAssert = "premise y >= 0\npremise x + y == 10\ngoal x <= 10";
    private const string RefutedAssert = "premise x + y == 10\npremise x > 4\ngoal x < 100";
    private const string VacuousAssert = "premise x > 5\npremise x < 3\ngoal x == 0";
    private const string OutOfFragmentAssert = "premise x * x == 4\ngoal x == 2";

    // ── 缺失≠错误: 放行且不追问 ────────────────────────────────────────

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   \n\t ")]
    [InlineData("帮我把 CI 跑通, 不要动产品代码")]
    public void AbsentOrProse_IsProceed(string? text)
    {
        var d = PlanNodeFormalGate.Evaluate(text);
        Assert.True(d.Allowed);
        Assert.Equal(FormalGateDisposition.Proceed, d.Disposition);
        Assert.Equal("no_formal_absent", d.ReasonCode);
        Assert.Equal("NoFormal", d.VerdictText);
    }

    [Theory]
    [InlineData("no_formal: 该节点只做资源下载")]
    [InlineData("NO_FORMAL")]
    public void ExplicitNoFormal_IsProceed(string text)
    {
        var d = PlanNodeFormalGate.Evaluate(text);
        Assert.True(d.Allowed);
        Assert.Equal("no_formal_declared", d.ReasonCode);
    }

    // ── 已证 ⇒ 放行 ──────────────────────────────────────────────────

    [Fact]
    public void ProvedAssertion_IsAllowed()
    {
        var d = PlanNodeFormalGate.Evaluate(ProvedAssert);
        Assert.True(d.Allowed);
        Assert.Equal(FormalGateDisposition.Proceed, d.Disposition);
        Assert.Equal("proved", d.ReasonCode);
        Assert.Equal("Proved", d.VerdictText);
        Assert.NotNull(d.AssertText);
        Assert.True(d.Ms >= 0);
    }

    // ── 反驳 ⇒ 阻断 + 精确反例 ────────────────────────────────────────

    [Fact]
    public void RefutedAssertion_IsBlockedWithCounterexample()
    {
        var d = PlanNodeFormalGate.Evaluate(RefutedAssert);
        Assert.False(d.Allowed);
        Assert.Equal(FormalGateDisposition.Violation, d.Disposition);
        Assert.Equal("refuted", d.ReasonCode);
        Assert.NotNull(d.Counterexample);
        Assert.Contains("x=", d.Counterexample);
        Assert.Contains("y=", d.Counterexample);
        Assert.Contains("反例", PlanNodeFormalGate.BlockMessage(d));
    }

    [Fact]
    public void CounterexampleFormatting_IsDeterministic()
    {
        var a = PlanNodeFormalGate.Evaluate(RefutedAssert);
        var b = PlanNodeFormalGate.Evaluate(RefutedAssert);
        Assert.Equal(a.Counterexample, b.Counterexample);
        Assert.Equal(a.VerdictText, b.VerdictText);
    }

    // ── 空真(前提不可满足) ⇒ 阻断, 不是证据 ───────────────────────────

    [Fact]
    public void VacuousAssertion_IsBlocked()
    {
        var d = PlanNodeFormalGate.Evaluate(VacuousAssert);
        Assert.False(d.Allowed);
        Assert.Equal(FormalGateDisposition.Violation, d.Disposition);
        Assert.Equal("premises_unsat_over_integers", d.ReasonCode);
        Assert.Equal("Vacuous", d.VerdictText);
    }

    // ── 片段外 ⇒ 弃权: 不放行, 但**不计违规**(DCR 口径) ────────────────

    [Fact]
    public void OutOfFragment_IsAbstained_NotViolation()
    {
        var d = PlanNodeFormalGate.Evaluate(OutOfFragmentAssert);
        Assert.False(d.Allowed);
        Assert.Equal(FormalGateDisposition.Abstained, d.Disposition);
        Assert.StartsWith("fragment_limit", d.ReasonCode);
        Assert.Equal("Unknown", d.VerdictText);
    }

    // ── 畸形 ⇒ 阻断(模型不能靠写坏断言绕过闸门) ───────────────────────

    [Theory]
    [InlineData("premise x > 4")]                       // 缺 goal
    [InlineData("goal x < 10")]                          // 缺 premise
    [InlineData("premise\ngoal x < 1")]                  // 裸关键字
    [InlineData("no_formal: 懒\npremise x > 4\ngoal x < 10")] // 自相矛盾
    public void MalformedContract_IsBlocked(string text)
    {
        var d = PlanNodeFormalGate.Evaluate(text);
        Assert.False(d.Allowed);
        Assert.Equal(FormalGateDisposition.Malformed, d.Disposition);
    }

    // ── 铁律: 任何分支都不得产生 LLM 调用 ─────────────────────────────

    [Theory]
    [InlineData(null)]
    [InlineData("no_formal: x")]
    [InlineData(ProvedAssert)]
    [InlineData(RefutedAssert)]
    [InlineData(VacuousAssert)]
    [InlineData(OutOfFragmentAssert)]
    [InlineData("premise x > 4")]
    public void NeverCallsLlm(string? text)
    {
        var d = PlanNodeFormalGate.Evaluate(text);
        Assert.False(d.WouldCallLlm);
        Assert.True(d.Ms < 5_000, "本地判定必须远快于任何 LLM 往返");
    }

    // ── 消融开关 (负向控制: =0 时 DCR 对照组必须退化) ─────────────────

    [Fact]
    public void Switch_DefaultEnabled_ZeroDisables()
    {
        var saved = Environment.GetEnvironmentVariable(PlanNodeFormalGate.EnvSwitch);
        try
        {
            Environment.SetEnvironmentVariable(PlanNodeFormalGate.EnvSwitch, null);
            Assert.True(PlanNodeFormalGate.IsEnabled());

            Environment.SetEnvironmentVariable(PlanNodeFormalGate.EnvSwitch, "0");
            Assert.False(PlanNodeFormalGate.IsEnabled());

            Environment.SetEnvironmentVariable(PlanNodeFormalGate.EnvSwitch, "1");
            Assert.True(PlanNodeFormalGate.IsEnabled());
        }
        finally
        {
            Environment.SetEnvironmentVariable(PlanNodeFormalGate.EnvSwitch, saved);
        }
    }
}
