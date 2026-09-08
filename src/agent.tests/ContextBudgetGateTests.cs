using agent.exploration;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.13.3 M2 — 上下文预算门单测 (用户钦定 Baseline 换血前置)。
/// 更正2 语义: est &lt; WARN → normal; ≥WARN → isolated_micro; ≥HARD → hard_drop; 边界防抖。
/// </summary>
public class ContextBudgetGateTests
{
    private static ContextBudgetGate New(int warn = 6000, int hard = 9000) =>
        new(new ContextGateConfig { WarnThreshold = warn, HardThreshold = hard, ExpectedOutputTokens = 512 });

    [Fact]
    public void Small_Prompt_Normal_Mode()
    {
        // 现状形态: prompt 700 + out 512 = 1212 < 6000 → normal (更正2: 零改动):
        var v = New().Evaluate(700);
        Assert.Equal(ContextGateMode.Normal, v.Mode);
    }

    [Fact]
    public void Over_Warn_Triggers_IsolatedMicro()
    {
        var v = New().Evaluate(6000); // 6000+512=6512 ≥ 6000
        Assert.Equal(ContextGateMode.IsolatedMicro, v.Mode);
    }

    [Fact]
    public void Over_Hard_Triggers_HardDrop()
    {
        var v = New().Evaluate(8800); // 8800+512=9312 ≥ 9000
        Assert.Equal(ContextGateMode.HardDrop, v.Mode);
    }

    [Fact]
    public void Hysteresis_Keeps_Last_Decision_Near_Boundary()
    {
        // MS-F04: 模式稳定后 (≥3 次判定), est 在阈值 ±5% 内的边界请求维持上次决策 (防抖):
        // 首次跨越必须放行 (python 复现抓的 bug: 首次被防抖弹回, 门永远打不开):
        var gate = New();
        Assert.Equal(ContextGateMode.IsolatedMicro, gate.Evaluate(6000).Mode);  // 1: 6512 跨越 → micro 放行
        Assert.Equal(ContextGateMode.IsolatedMicro, gate.Evaluate(6100).Mode);  // 2: 稳定 micro
        var third = gate.Evaluate(5560);                                        // 3: 6072 ≥6000 自然 micro
        Assert.Equal(ContextGateMode.IsolatedMicro, third.Mode);
        var fourth = gate.Evaluate(5388);                                       // 4: 5900 <6000 自然 normal, 但边界 100<300 → 维持 micro
        Assert.Equal(ContextGateMode.IsolatedMicro, fourth.Mode);
        Assert.Contains("hysteresis", fourth.Reason);
        var fifth = gate.Evaluate(3000);                                        // 远离边界 → 正常回 normal
        Assert.Equal(ContextGateMode.Normal, fifth.Mode);
    }

    [Fact]
    public void Far_Below_Boundary_Switches_Back()
    {
        var gate = New();
        gate.Evaluate(6000); // micro
        var v = gate.Evaluate(3000); // 3512, 远离边界 → normal
        Assert.Equal(ContextGateMode.Normal, v.Mode);
    }

    [Fact]
    public void HardDrop_Never_Hysteresized()
    {
        var gate = New();
        gate.Evaluate(6000); // micro
        var v = gate.Evaluate(8800); // ≥ hard → hard drop (不防抖)
        Assert.Equal(ContextGateMode.HardDrop, v.Mode);
    }
}
