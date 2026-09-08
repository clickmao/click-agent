using agent.modelqueue;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.12.0 B2 — 渲染插件真机测试: SkiaSharp (SKIA_RENDERER) 与 SVG 文本双插件。
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

#if SKIA_RENDERER
    [Fact]
    public void SkiaSharp_Plugin_Renders_Png_When_Available()
    {
        var plugin = new SkiaSharpRenderPlugin();
        if (!plugin.IsAvailable) return; // native 缺失环境 (CI) 跳过 — IsAvailable 已诚实探测
        var path = Path.Combine(Path.GetTempPath(), $"img_{Guid.NewGuid():N}.png");
        var r = plugin.Render(SampleShapes(), 256, 256, path);
        Assert.True(r.Ok, r.Error);
        Assert.True(r.FileBytes > 200);
        Assert.Equal(".png", Path.GetExtension(path));
    }
#endif

    [Fact]
    public void Registry_Falls_Back_To_Svg_When_Skia_Disabled()
    {
        // 无 Skia 注册 → svg-text 兜底 (边缘选项停编 Skia 后的运行时形态)
        var registry = new ImageRenderPluginRegistry(new IImageRenderPlugin[] { new SvgTextRenderPlugin() });
        Assert.True(registry.HasRenderer);
        Assert.Equal("svg-text", registry.GetDefault()!.Name);
    }

    [Fact]
    public void Registry_Empty_HasRenderer_False()
    {
        // 全插件不可用 → HasRenderer=false → image-gen 跳过后续环节 (用户钦定)
        var registry = new ImageRenderPluginRegistry(Array.Empty<IImageRenderPlugin>());
        Assert.False(registry.HasRenderer);
        Assert.Null(registry.GetDefault());
    }
}
