using System.Text;
using agent.config;

namespace agent.modelqueue;

/// <summary>
/// v0.12.0 R210 (用户钦定) — 纯 SVG 文本 Local Renderer:
/// LLM 输出结构化绘图 DSL (JSON shapes[]) → 本地拼装 SVG 字符串 → .svg 落盘。
/// 零第三方依赖 / 零 native / 零外部进程 — AOT 天然安全 (不用 SkiaSharp, 用户钦定纯 SVG 文本方向)。
/// 渲染产物: .svg (浏览器/图片查看器直开); 若需 PNG 由外部工具链后续转换 (不在本期)。
/// 打点: render_call (kv: shapes, ms, ok, svg_bytes)。
/// </summary>
public static class LocalSvgRenderer
{
    /// <summary>DSL 形状 (受限词表: rect/circle/line/text — 语法可靠性优先)</summary>
    public sealed class Shape
    {
        public string Type { get; set; } = "rect";
        public int X { get; set; }
        public int Y { get; set; }
        public int W { get; set; } = 32;
        public int H { get; set; } = 32;
        public int R { get; set; }              // circle 半径
        public int X2 { get; set; }             // line 终点
        public int Y2 { get; set; }
        public string Fill { get; set; } = "#89b4fa";
        public string TextContent { get; set; } = string.Empty;
        public int FontSize { get; set; } = 14;
    }

    public sealed class RenderResult
    {
        public bool Ok { get; set; }
        public string? SvgPath { get; set; }
        public long SvgBytes { get; set; }
        public string? Error { get; set; }
        public int WallMs { get; set; }
        public int ShapeCount { get; set; }
    }

    /// <summary>
    /// 渲染 DSL shapes → SVG 文件。失败不抛异常 (结果对象携带 Error, 打点不影响主链路)。
    /// </summary>
    public static RenderResult Render(IEnumerable<Shape> shapes, int width, int height,
        string savePath, string title = "render", CancellationToken ct = default)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var result = new RenderResult();
        try
        {
            var sb = new StringBuilder();
            sb.Append($"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\">");
            sb.Append($"<title>{Esc(title)}</title>");
            sb.Append($"<rect width=\"{width}\" height=\"{height}\" fill=\"#1e1e2e\"/>");
            var count = 0;
            foreach (var s in shapes)
            {
                ct.ThrowIfCancellationRequested();
                switch (s.Type)
                {
                    case "rect":
                        sb.Append($"<rect x=\"{s.X}\" y=\"{s.Y}\" width=\"{s.W}\" height=\"{s.H}\" fill=\"{Esc(s.Fill)}\"/>");
                        break;
                    case "circle":
                        sb.Append($"<circle cx=\"{s.X}\" cy=\"{s.Y}\" r=\"{Math.Max(1, s.R)}\" fill=\"{Esc(s.Fill)}\"/>");
                        break;
                    case "line":
                        sb.Append($"<line x1=\"{s.X}\" y1=\"{s.Y}\" x2=\"{s.X2}\" y2=\"{s.Y2}\" stroke=\"{Esc(s.Fill)}\" stroke-width=\"2\"/>");
                        break;
                    case "text":
                        sb.Append($"<text x=\"{s.X}\" y=\"{s.Y}\" fill=\"{Esc(s.Fill)}\" font-size=\"{s.FontSize}\" font-family=\"monospace\">{Esc(s.TextContent)}</text>");
                        break;
                    default:
                        continue; // 未知形状跳过 (不崩 — DSL 受限词表外的项忽略)
                }
                count++;
            }
            sb.Append("</svg>");
            var svgText = sb.ToString();

            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(savePath))!);
            File.WriteAllText(savePath, svgText, new UTF8Encoding(false));
            result.Ok = true;
            result.SvgPath = savePath;
            result.SvgBytes = new FileInfo(savePath).Length;
            result.ShapeCount = count;
            return Finish(result, sw);
        }
        catch (OperationCanceledException) when (ct.IsCancellationRequested)
        {
            result.Error = "cancelled";
            return Finish(result, sw);
        }
        catch (Exception ex)
        {
            result.Error = ex.Message.Length <= 200 ? ex.Message : ex.Message[..200];
            return Finish(result, sw);
        }
    }

    private static string Esc(string s) => s
        .Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;").Replace("\"", "&quot;");

    private static RenderResult Finish(RenderResult r, System.Diagnostics.Stopwatch sw)
    {
        r.WallMs = (int)sw.ElapsedMilliseconds;
        try
        {
            AgentTelemetry.Emit("render_call", "LocalSvgRenderer",
                ("shapes", r.ShapeCount),
                ("ms", r.WallMs),
                ("ok", r.Ok),
                ("svg_bytes", r.SvgBytes),
                ("error", r.Error));
        }
        catch { }
        return r;
    }
}
