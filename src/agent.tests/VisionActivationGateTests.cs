using agent.vision;
using Xunit;

namespace agent.tests;

/// <summary>远端 → 本地视觉模型 的**按需加载闸**判据（内存硬约束 + 真假判定不在本地）。</summary>
public class VisionActivationGateTests
{
    private static readonly ScreenTaskSignal ScreenUi = new(true, "screenshot_ui", "在设置里关闭更新提示");

    [Fact]
    public void NoSignal_NeverLoads()
    {
        var d = VisionActivationGate.Decide(ScreenTaskSignal.None, modelPresent: true, visionRunning: false, otherLocalProcessRunning: false);
        Assert.False(d.Load);
        Assert.Equal(VisionActivationGate.CodeSkipNoSignal, d.ReasonCode);
    }

    [Fact]
    public void ScreenTask_ModelPresent_Idle_Loads()
    {
        var d = VisionActivationGate.Decide(ScreenUi, modelPresent: true, visionRunning: false, otherLocalProcessRunning: false);
        Assert.True(d.Load);
        Assert.Equal(VisionActivationGate.CodeLoad, d.ReasonCode);
    }

    [Fact]
    public void ScreenTask_ModelMissing_Skips()
    {
        var d = VisionActivationGate.Decide(ScreenUi, modelPresent: false, visionRunning: false, otherLocalProcessRunning: false);
        Assert.False(d.Load);
        Assert.Equal(VisionActivationGate.CodeSkipModelMissing, d.ReasonCode);
    }

    [Fact]
    public void ScreenTask_OtherLocalProcessRunning_Skips_NoConcurrency()
    {
        var d = VisionActivationGate.Decide(ScreenUi, modelPresent: true, visionRunning: false, otherLocalProcessRunning: true);
        Assert.False(d.Load);
        Assert.Equal(VisionActivationGate.CodeSkipBusy, d.ReasonCode);
    }

    [Fact]
    public void ScreenTask_AlreadyRunning_ReusesInsteadOfRestart()
    {
        var d = VisionActivationGate.Decide(ScreenUi, modelPresent: true, visionRunning: true, otherLocalProcessRunning: true);
        Assert.True(d.Load);
        Assert.Equal(VisionActivationGate.CodeReuse, d.ReasonCode);
    }

    [Fact]
    public void NonScreenKind_Skips()
    {
        var d = VisionActivationGate.Decide(new ScreenTaskSignal(true, "none", string.Empty), modelPresent: true, visionRunning: false, otherLocalProcessRunning: false);
        Assert.False(d.Load);
        Assert.Equal(VisionActivationGate.CodeSkipNotScreenKind, d.ReasonCode);
    }

    [Fact]
    public void LocalUnavailability_DoesNotChangeRemoteVerdict()
    {
        // 真假定性在远端: 本地模型缺失只影响「能否加载」, 不改变「是不是屏幕任务」这一判定
        var signal = ScreenTaskSignal.Parse("{\"vision\":{\"needed\":true,\"kind\":\"element_grounding\",\"subgoal\":\"点保存\"}}");
        Assert.True(signal.Needed);
        Assert.Equal("element_grounding", signal.Kind);
        var missing = VisionActivationGate.Decide(signal, modelPresent: false, visionRunning: false, otherLocalProcessRunning: false);
        Assert.False(missing.Load);
        Assert.True(signal.Needed);
    }
}
