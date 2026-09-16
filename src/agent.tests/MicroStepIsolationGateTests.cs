using agent.exploration;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R485 微问询形态分流闸 — 单测。
/// 设计前提 (原理性): 隔离微通道 = system(隔离声明) + user(微问题原文), **无前文**
/// ⇒ 回指在通道内不可解, 命中回指标记即预发送拦截 (省一次必然无效的远端调用)。
/// 非回指 (自足) 微问询必须放行 (宁漏勿伤: 误伤会丢信息, 漏网只少省一次调用)。
/// 真机流量锚点: eval/rover/r482/calls-Arole.jsonl 的 7 条微步骤隔离问询 (已提交产物)。
/// </summary>
public class MicroStepIsolationGateTests
{
    // ---- 真机录制的 7 条回指微问询 (逐字来自 calls-Arole.jsonl / calls-R.jsonl) ----
    [Theory]
    [InlineData("换个说法")]
    [InlineData("从头再说")]
    [InlineData("你上一条说 3 加 5 等于 9，对吧？")]
    [InlineData("你上一条说的数是九")]
    [InlineData("不对，你上一条不准确，请重新确认")]
    [InlineData("刚才那个结果再确认一下")]
    [InlineData("上一句 的答案是几")]
    public void AnaphoraDependent_IsBlocked(string microQuestion)
    {
        var d = MicroStepIsolationGate.Decide(microQuestion);
        Assert.False(d.Send, $"回指微问询应被拦截: {microQuestion}");
        Assert.Equal("isolation_invalid_anaphora", d.Reason);
    }

    // ---- 负控: 自足微问询必须放行 (拦截即误伤 ⇒ 丢信息) ----
    [Theory]
    [InlineData("把构建命令写成一行。")]
    [InlineData("计算 3 加 5 的结果")]
    [InlineData("列出 .NET 10 的三个新特性")]
    [InlineData("解释递归与迭代的区别")]
    [InlineData("继续解释递归与迭代的区别")] // known_miss: 『继续』刻意不上列表 (词面过泛)
    public void SelfContained_IsSent(string microQuestion)
    {
        var d = MicroStepIsolationGate.Decide(microQuestion);
        Assert.True(d.Send, $"自足微问询应放行: {microQuestion}");
    }

    // ---- 空/空白: 无问题可问 ⇒ 不发 (省调用且零信息) ----
    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("\n\t ")]
    public void Blank_IsBlocked(string microQuestion)
    {
        var d = MicroStepIsolationGate.Decide(microQuestion);
        Assert.False(d.Send);
        Assert.Equal("blank", d.Reason);
    }

    [Fact]
    public void Null_IsBlocked()
    {
        var d = MicroStepIsolationGate.Decide(null);
        Assert.False(d.Send);
        Assert.Equal("blank", d.Reason);
    }

    /// <summary>
    /// 判定必须与两侧包裹文本无关: 产品把微问题包进 '[微步骤隔离问询] …\n(只回答本微问题, 不引申)' 后再发,
    /// 分类只看微问题原文 (包裹文本自身不含回指标记, 不得成为放行/拦截的来源)。
    /// </summary>
    [Fact]
    public void Decision_DependsOnlyOnQuestionText()
    {
        Assert.False(MicroStepIsolationGate.Decide("换个说法").Send);
        Assert.True(MicroStepIsolationGate.Decide("把构建命令写成一行。").Send);
        // 标记表非空自检 (空表 = 闸失效, 必须由测试而非运行期发现)
        Assert.True(MicroStepIsolationGate.AnaphoraMarkers.Count > 0);
        Assert.Contains("上一条", MicroStepIsolationGate.AnaphoraMarkers);
        // 刻意排除的过泛词, 防止后续被"顺手"加回
        Assert.DoesNotContain("继续", MicroStepIsolationGate.AnaphoraMarkers);
        Assert.DoesNotContain("接着", MicroStepIsolationGate.AnaphoraMarkers);
    }

    /// <summary>打点/审计要求: 判定结果要能给出可落盘的原因与命中标记 (不含用户正文以外的信息)。</summary>
    [Fact]
    public void Decision_CarriesMarkerForAudit()
    {
        var d = MicroStepIsolationGate.Decide("你上一条说的数是九");
        Assert.False(d.Send);
        Assert.Equal("上一条", d.Marker);
        var ok = MicroStepIsolationGate.Decide("解释递归与迭代的区别");
        Assert.True(ok.Send);
        Assert.Equal("", ok.Marker);
    }
}
