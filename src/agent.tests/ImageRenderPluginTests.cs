using agent.modelqueue;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.12.0 B2 — 渲染插件真机测试 (R351: SkiaSharp 插件移除, 仅 SVG 文本插件)。
/// </summary>
public class ImageRenderPluginTests
{
    private static List<LocalSvgRenderer.Shape> SampleShapes() => new()
    {
        new() { Type = "rect", X = 32, Y = 32, W = 64, H = 64, Fill = "#f38ba8" },
        new() { Type = "circle", X = 180, Y = 96, R = 40, Fill = "#a6e3a1" },
        new() { Type = "text", X = 32, Y = 200, TextContent = "plugin test", Fill = "#cdd6f4" },
    };

    [Fact]
    public void SvgText_Plugin_Always_Available_Renders()
    {
        var plugin = new SvgTextRenderPlugin();
        Assert.True(plugin.IsAvailable);
        var path = Path.Combine(Path.GetTempPath(), $"img_{Guid.NewGuid():N}.{plugin.OutputExtension}");
        var r = plugin.Render(SampleShapes(), 256, 256, path);
        Assert.True(r.Ok, r.Error);
        Assert.True(r.FileBytes > 100);
        Assert.Contains("<svg", File.ReadAllText(path));
    }
}
