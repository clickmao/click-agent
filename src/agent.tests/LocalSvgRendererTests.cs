using agent.modelqueue;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.12.0 R210 — LocalSvgRenderer (纯 SVG 文本 local renderer, 用户钦定方向) 对抗测试。
/// 零依赖: 只验证 DSL→SVG 字符串拼装与落盘, 不依赖任何渲染 native。
/// </summary>
public class LocalSvgRendererTests
{
    [Fact]
    public void Renders_Shapes_To_Svg_File()
    {
        var shapes = new List<LocalSvgRenderer.Shape>
        {
            new() { Type = "rect", X = 32, Y = 32, W = 64, H = 64, Fill = "#f38ba8" },
            new() { Type = "circle", X = 180, Y = 96, R = 40, Fill = "#a6e3a1" },
            new() { Type = "line", X = 10, Y = 10, X2 = 240, Y2 = 240, Fill = "#89b4fa" },
            new() { Type = "text", X = 32, Y = 200, TextContent = "Renderer OK", Fill = "#cdd6f4" },
        };
        var path = Path.Combine(Path.GetTempPath(), $"svgtest_{Guid.NewGuid():N}.svg");
        var r = LocalSvgRenderer.Render(shapes, 256, 256, path, "test");
        Assert.True(r.Ok, r.Error);
        Assert.Equal(4, r.ShapeCount);
        Assert.True(r.SvgBytes > 100);
        var text = File.ReadAllText(path);
        Assert.Contains("<svg xmlns=\"http://www.w3.org/2000/svg\"", text);
        Assert.Contains("<rect x=\"32\"", text);
        Assert.Contains("<circle cx=\"180\"", text);
        Assert.Contains("Renderer OK", text);
    }

    [Fact]
    public void Xml_Escapes_Text_Content()
    {
        // 文本含 <>&" — 必须转义 (非法 XML 会让查看器打不开)
        var shapes = new List<LocalSvgRenderer.Shape>
        {
            new() { Type = "text", X = 10, Y = 10, TextContent = "a<b>&c\"d" },
        };
        var path = Path.Combine(Path.GetTempPath(), $"svgtest_{Guid.NewGuid():N}.svg");
        var r = LocalSvgRenderer.Render(shapes, 128, 128, path);
        Assert.True(r.Ok);
        var text = File.ReadAllText(path);
        Assert.Contains("a&lt;b&gt;&amp;c&quot;d", text);
        Assert.DoesNotContain("a<b>", text);
    }

    [Fact]
    public void Unknown_Shape_Type_Is_Skipped_Not_Fatal()
    {
        var shapes = new List<LocalSvgRenderer.Shape>
        {
            new() { Type = "pixel-grid" },   // 词表外 — 跳过不崩
            new() { Type = "rect", X = 0, Y = 0, W = 10, H = 10 },
        };
        var path = Path.Combine(Path.GetTempPath(), $"svgtest_{Guid.NewGuid():N}.svg");
        var r = LocalSvgRenderer.Render(shapes, 64, 64, path);
        Assert.True(r.Ok);
        Assert.Equal(1, r.ShapeCount);
    }
}
