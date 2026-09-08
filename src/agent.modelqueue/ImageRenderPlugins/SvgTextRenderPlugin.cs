namespace agent.modelqueue;

/// <summary>
/// SVG 文本渲染插件 (零依赖兜底, 恒可用) — 复用 LocalSvgRenderer 拼装。
/// </summary>
public sealed class SvgTextRenderPlugin : IImageRenderPlugin
{
    public string Name => "svg-text";
    public string OutputExtension => "svg";
    public bool IsAvailable => true; // 零依赖, 恒可用

    public ImageRenderResult Render(IReadOnlyList<LocalSvgRenderer.Shape> shapes, int width, int height, string savePath, CancellationToken ct = default)
    {
        var r = LocalSvgRenderer.Render(shapes, width, height, savePath, ct: ct);
        return new ImageRenderResult { Ok = r.Ok, Path = r.SvgPath, FileBytes = r.SvgBytes, Error = r.Error, WallMs = r.WallMs };
    }
}
