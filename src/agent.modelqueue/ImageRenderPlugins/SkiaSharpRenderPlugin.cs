#if SKIA_RENDERER
using SkiaSharp;

namespace agent.modelqueue;

/// <summary>
/// SkiaSharp 渲染插件 (默认) — DSL shapes → 程序化绘制 → PNG。
/// 边缘选项: agent.modelqueue.csproj 定义 SKIA_RENDERER (默认开);
/// 构建时 -p:DisableSkiaRenderer=true → 本文件不编译, 插件消失, 注册表只剩 svg-text。
/// 真机验证: /tmp/svgprobe 4.148 + NativeAssets.Linux 渲染 PNG ✓ (2026-09-08)。
/// </summary>
public sealed class SkiaSharpRenderPlugin : IImageRenderPlugin
{
    public string Name => "skiasharp";
    public string OutputExtension => "png";

    /// <summary>可用性 = SKBitmap 能初始化 (native 资产加载探测, 一次)。</summary>
    private static readonly bool _available = Probe();
    public bool IsAvailable => _available;

    private static bool Probe()
    {
        try
        {
            using var bmp = new SKBitmap(8, 8);
            return true;
        }
        catch { return false; } // DllNotFoundException 等 → 不可用
    }

    public ImageRenderResult Render(IReadOnlyList<LocalSvgRenderer.Shape> shapes, int width, int height, string savePath, CancellationToken ct = default)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var result = new ImageRenderResult();
        try
        {
            using var bitmap = new SKBitmap(width, height);
            using var canvas = new SKCanvas(bitmap);
            canvas.Clear(new SKColor(0x1e, 0x1e, 0x2e));
            foreach (var s in shapes)
            {
                using var paint = new SKPaint { Color = SKColor.Parse(s.Fill), IsAntialias = false };
                switch (s.Type)
                {
                    case "rect": canvas.DrawRect(s.X, s.Y, s.W, s.H, paint); break;
                    case "circle": canvas.DrawCircle(s.X, s.Y, Math.Max(1, s.R), paint); break;
                    case "line":
                        canvas.DrawLine(s.X, s.Y, s.X2, s.Y2, new SKPaint { Color = paint.Color, StrokeWidth = 2, IsAntialias = false });
                        break;
                    case "text":
                        using (var font = new SKFont(SKTypeface.FromFamilyName("monospace"), s.FontSize))
                            canvas.DrawText(s.TextContent, s.X, s.Y, font, paint);
                        break;
                }
            }
            using var img = SKImage.FromBitmap(bitmap);
            using var data = img.Encode(SKEncodedImageFormat.Png, 100);
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(savePath))!);
            File.WriteAllBytes(savePath, data.ToArray());
            result.Ok = true;
            result.Path = savePath;
            result.FileBytes = data.Size;
            result.WallMs = (int)sw.ElapsedMilliseconds;
            return result;
        }
        catch (Exception ex)
        {
            result.Error = ex.Message.Length <= 200 ? ex.Message : ex.Message[..200];
            result.WallMs = (int)sw.ElapsedMilliseconds;
            return result;
        }
    }
}
#endif
