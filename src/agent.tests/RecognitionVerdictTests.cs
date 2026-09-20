using agent.nlp;
using Xunit;

namespace agent.tests;

/// <summary>
/// RF0004.1 (M1) 识别出口的判据面机检:
///   ① 正控: 本地消化轮 ⇒ {标签, abstain=0}; 未消化轮 ⇒ {abstain, 依据含机制原因};
///   ② 负控 (轴有牙): 显式 off/0 ⇒ 出口关; 缺省/其他值 ⇒ 开 (缺省翻档必须可判);
///   ③ 零回归机理: 出口渲染**只读** (不递增 NlpGate 计数、不写库) —— 这是「开关开/关逐位等价」的根据;
///   ④ 确定性 ∧ 非平凡 (成对): 同输入逐位相同 ∧ 不同输入读数互异 (防「恒定输出冒充可复现」)。
/// </summary>
public sealed class RecognitionVerdictTests
{
    [Fact]
    public void Recognized_LocalConsumed_LabelIsFace_AndRenderIsLabelPipeEvidence()
    {
        var v = RecognitionOutlet.Render(true, "mechanical:repeat→local", "repeat", 12, "abcdef0123456789");
        Assert.False(v.Abstain);
        Assert.Equal("repeat", v.Label);
        Assert.Contains("basis=mechanical:repeat→local", v.Evidence, System.StringComparison.Ordinal);
        Assert.Contains("face=repeat", v.Evidence, System.StringComparison.Ordinal);
        Assert.Contains("len=12", v.Evidence, System.StringComparison.Ordinal);
        Assert.StartsWith("repeat|", v.Render(), System.StringComparison.Ordinal);
    }

    [Fact]
    public void Abstained_NotConsumed_LabelIsAbstainConstant_AndEvidenceCarriesReason()
    {
        var v = RecognitionOutlet.Render(false, "mechanical:pass→remote", string.Empty, 7, "ffffffffffffffff");
        Assert.True(v.Abstain);
        Assert.Equal(RecognitionVerdict.AbstainLabel, v.Label);
        Assert.Contains("basis=mechanical:pass→remote", v.Evidence, System.StringComparison.Ordinal);
        Assert.Contains("face=gate", v.Evidence, System.StringComparison.Ordinal);   // 无族面 ⇒ 缺省面标
        Assert.StartsWith("abstain|", v.Render(), System.StringComparison.Ordinal);
    }

    [Theory]
    [InlineData(null, true)]        // 缺省 ⇒ 开 (出口落地为产品缺省)
    [InlineData("on", true)]
    [InlineData("1", true)]
    [InlineData("OFF", false)]      // 显式关 (大小写不敏感)
    [InlineData("off", false)]
    [InlineData("0", false)]
    [InlineData("yes", true)]       // 未识别值 ⇒ 开 (不静默关: 关只能由显式 off/0 触发)
    public void Axis_ExplicitOffDisables_OthersStayOn(string? raw, bool expected)
    {
        Assert.Equal(expected, RecognitionOutlet.IsEnabled(raw));
    }

    [Fact]
    public void Render_IsReadOnly_NoCounterSideEffects()
    {
        // 零回归机理的根据: 出口渲染不得触碰判定面计数 (计数被 Decide/Observe 递增)
        var before = NlpGate.Counters;
        for (var i = 0; i < 5; i++)
        {
            _ = RecognitionOutlet.Render(i % 2 == 0, "learned-shape", "para", i, "0123456789abcdef");
        }
        var after = NlpGate.Counters;
        Assert.Equal(before.LocalHits, after.LocalHits);
        Assert.Equal(before.Escalations, after.Escalations);
        Assert.Equal(before.Learned, after.Learned);
    }

    [Fact]
    public void Render_Deterministic_AndNonTrivial()
    {
        var a1 = RecognitionOutlet.Render(true, "gate:skip→local", "repeat", 5, "aaaaaaaaaaaaaaaa").Render();
        var a2 = RecognitionOutlet.Render(true, "gate:skip→local", "repeat", 5, "aaaaaaaaaaaaaaaa").Render();
        var b = RecognitionOutlet.Render(false, "mechanical:pass→remote", "repeat", 5, "aaaaaaaaaaaaaaaa").Render();
        Assert.Equal(a1, a2);                       // 确定性: 同输入逐位相同
        Assert.NotEqual(a1, b);                     // 非平凡: 判定面不同 ⇒ 读数必须互异
        Assert.NotEqual(
            RecognitionOutlet.Render(true, "gate:skip→local", "para", 5, "aaaaaaaaaaaaaaaa").Render(),
            a1);                                    // 面标参与读数 (非恒等常量)
    }
}
