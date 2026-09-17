using agent.vision;
using Xunit;

namespace agent.tests;

/// <summary>远端结构化输出里的 vision 信号解析判据（fail-closed、与外层契约解耦）。</summary>
public class ScreenTaskSignalTests
{
    [Fact]
    public void Needed_ScreenKind_Parsed()
    {
        var s = ScreenTaskSignal.Parse("{\"vision\":{\"needed\":true,\"kind\":\"screenshot_ui\",\"subgoal\":\"关闭更新弹窗\"}}");
        Assert.True(s.Needed);
        Assert.Equal("screenshot_ui", s.Kind);
        Assert.Equal("关闭更新弹窗", s.Subgoal);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("not json")]
    [InlineData("{}")]
    [InlineData("{\"vision\":null}")]
    [InlineData("{\"vision\":{\"kind\":\"screenshot_ui\"}}")]
    [InlineData("{\"vision\":{\"needed\":\"true\",\"kind\":\"screenshot_ui\"}}")]
    [InlineData("{\"vision\":{\"needed\":true,\"kind\":\"drag\"}}")]
    [InlineData("{\"vision\":{\"needed\":true,\"kind\":\"none\"}}")]
    [InlineData("{\"vision\":{\"needed\":false,\"kind\":\"screenshot_ui\"}}")]
    public void Malformed_OrConflicting_YieldsNone(string? json)
    {
        var s = ScreenTaskSignal.Parse(json);
        Assert.False(s.Needed);
        Assert.Equal("none", s.Kind);
    }

    [Fact]
    public void ExplicitNone_IsStableDefault()
    {
        var s = ScreenTaskSignal.Parse("{\"vision\":{\"needed\":false,\"kind\":\"none\"}}");
        Assert.False(s.Needed);
        Assert.Equal(ScreenTaskSignal.None, s);
    }
}
