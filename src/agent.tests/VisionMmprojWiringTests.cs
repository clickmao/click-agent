using System;
using agent.llamacpp;
using Xunit;

namespace agent.tests;

/// <summary>
/// 视觉侧路接线判据 (LFM2.5-VL-3B): --mmproj 只在显式给出投影器时出现;
/// 缺失 ⇒ 启动前 fail-closed (ProviderUnavailable), 绝不静默降级成「纯文本但声称有视觉」。
/// </summary>
public class VisionMmprojWiringTests
{
    private static LlamaServerOptions Opt(string? mmproj) => new()
    {
        ModelPath = "/tmp/fake-model.gguf",
        MmprojPath = mmproj,
        ContextSize = 2048,
    };

    [Fact]
    public void Mmproj_Omitted_WhenNotSet()
    {
        var args = LlamaServerHost.BuildArgumentList(Opt(null), 18099, false);
        Assert.DoesNotContain("--mmproj", args);
    }

    [Fact]
    public void Mmproj_EmittedWithPath_WhenSet()
    {
        var args = LlamaServerHost.BuildArgumentList(Opt("/tmp/mmproj.gguf"), 18099, false);
        var i = args.IndexOf("--mmproj");
        Assert.True(i >= 0, "设置了 MmprojPath 就必须发 --mmproj");
        Assert.Equal("/tmp/mmproj.gguf", args[i + 1]);
    }

    [Fact]
    public void Describe_ExposesMmprojState()
    {
        Assert.Contains("mmproj=off", Opt(null).Describe(), StringComparison.Ordinal);
        Assert.Contains("mmproj=on", Opt("/tmp/mmproj.gguf").Describe(), StringComparison.Ordinal);
    }
}
