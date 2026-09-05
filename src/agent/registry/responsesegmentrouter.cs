using System.Text.RegularExpressions;

namespace agent.registry;

/// <summary>返回内容区段类型</summary>
public enum SegmentKind
{
    /// <summary>普通文本</summary>
    PlainText,

    /// <summary>fenced 代码块 (```lang ... ```), Language=语言标识</summary>
    Code,

    /// <summary>行内代码 (单反引号)</summary>
    InlineCode,
}

/// <summary>
/// LLM 返回内容的一段 — 快速标记的产物。
/// StartIndex/Length 指向原始文本, 供 UI 高亮/其他流程按区段取用, 无需复制字符串。
/// </summary>
public class ResponseSegment
{
    public SegmentKind Kind { get; init; }

    /// <summary>区段内容 (代码段不含围栏)</summary>
    public string Content { get; init; } = string.Empty;

    /// <summary>在原始全文中的偏移 (UI 定位用)</summary>
    public int StartIndex { get; init; }

    public int Length { get; init; }

    /// <summary>代码语言 (```html → "html")</summary>
    public string? Language { get; init; }

    /// <summary>路由到的插件名 (诊断/审计)</summary>
    public string? RoutedTo { get; set; }
}

/// <summary>
/// 区段插件接口 (v7.11): 返回内容后处理不写死 — 按区段类型路由到注册的插件。
/// 插件可消费标记 (如 UI 高亮 html 段) 或触发服务 (代码段→审查服务)。
/// </summary>
public interface IResponseSegmentPlugin
{
    /// <summary>插件名 (DI 唯一, 审计用)</summary>
    string Name { get; }

    /// <summary>声明消费的区段类型</summary>
    IReadOnlySet<SegmentKind> Consumes { get; }

    /// <summary>
    /// 处理一个区段。返回值进最终输出 (恒等返回即可透传)。
    /// 异步签名: 插件内部可调外部服务 (审查/渲染), 由宿主控制超时。
    /// </summary>
    Task<string> HandleAsync(ResponseSegment segment, CancellationToken ct = default);
}

/// <summary>
/// 快速区段标记器: 单遍扫描 (O(N), 无回溯正则) 把 LLM 返回文本切成区段序列。
/// 工业要点: "快速标记" — 只定位与分类, 不做语义处理; 消费逻辑全部在插件层。
/// </summary>
public static class ResponseSegmenter
{
    // fenced: 行首 ```lang (lang 可空) → 内容 → 行首 ```。行首锚定避免误匹配行内反引号。
    private static readonly Regex FenceOpen = new("(?m)^```([A-Za-z0-9+#._-]*)[ \\t]*\\r?\\n", RegexOptions.Compiled);
    private static readonly Regex FenceClose = new("(?m)^```[ \\t]*$", RegexOptions.Compiled);
    private static readonly Regex InlineCode = new("`([^`\\n]+)`", RegexOptions.Compiled);

    /// <summary>单遍切分: PlainText/Code/InlineCode 序列, StartIndex 精确覆盖全文</summary>
    public static List<ResponseSegment> Segment(string text)
    {
        var segments = new List<ResponseSegment>();
        var pos = 0;

        while (pos < text.Length)
        {
            var open = FenceOpen.Match(text, pos);
            if (!open.Success)
            {
                AddTextWithInline(segments, text, pos, text.Length - pos);
                break;
            }

            // 围栏前的纯文本
            if (open.Index > pos)
                AddTextWithInline(segments, text, pos, open.Index - pos);

            var close = FenceClose.Match(text, open.Index + open.Length);
            if (!close.Success)
            {
                // 未闭合围栏 → 按纯文本处理 (容错: LLM 输出可能截断)
                AddTextWithInline(segments, text, pos, text.Length - pos);
                break;
            }

            var lang = open.Groups[1].Value;
            var contentStart = open.Index + open.Length;
            segments.Add(new ResponseSegment
            {
                Kind = SegmentKind.Code,
                Content = text[contentStart..close.Index],
                StartIndex = contentStart,
                Length = close.Index - contentStart,
                Language = string.IsNullOrEmpty(lang) ? null : lang,
            });
            pos = close.Index + close.Length;
        }

        return segments;
    }

    /// <summary>纯文本段: 再切出行内代码 (保持 StartIndex 对齐原文)</summary>
    private static void AddTextWithInline(List<ResponseSegment> segments, string text, int start, int length)
    {
        var end = start + length;
        var pos = start;
        while (pos < end)
        {
            var m = InlineCode.Match(text, pos, end - pos);
            if (!m.Success)
            {
                segments.Add(MakePlain(text, pos, end - pos));
                break;
            }
            if (m.Index > pos)
                segments.Add(MakePlain(text, pos, m.Index - pos));

            var contentStart = m.Index + 1;
            segments.Add(new ResponseSegment
            {
                Kind = SegmentKind.InlineCode,
                Content = text[contentStart..(m.Index + m.Length - 1)],
                StartIndex = contentStart,
                Length = m.Length - 2,
            });
            pos = m.Index + m.Length;
        }
    }

    private static ResponseSegment MakePlain(string text, int start, int length) => new()
    {
        Kind = SegmentKind.PlainText,
        Content = text.Substring(start, length),
        StartIndex = start,
        Length = length,
    };
}

/// <summary>
/// 区段路由器: 按段类型分发到注册插件 (DI 注入, 不写死)。
/// 无插件消费的类型 → 内容原样透传 (默认行为, 零损耗)。
/// </summary>
public class ResponseSegmentRouter
{
    private readonly IReadOnlyList<IResponseSegmentPlugin> _plugins;
    private readonly Dictionary<SegmentKind, List<IResponseSegmentPlugin>> _routes;

    public ResponseSegmentRouter(IEnumerable<IResponseSegmentPlugin> plugins)
    {
        _plugins = plugins.ToList();
        _routes = new Dictionary<SegmentKind, List<IResponseSegmentPlugin>>();
        foreach (var p in _plugins)
        {
            foreach (var kind in p.Consumes)
            {
                if (!_routes.TryGetValue(kind, out var list))
                    _routes[kind] = list = new List<IResponseSegmentPlugin>();
                list.Add(p);
            }
        }
    }

    /// <summary>全部插件名 (诊断: 宿主启动时打印路由表)</summary>
    public IReadOnlyList<string> PluginNames => _plugins.Select(p => p.Name).ToList();

    /// <summary>处理全文: 标记 → 逐段路由 → 拼回输出 (插件可改写段内容)</summary>
    public async Task<string> ProcessAsync(string llmOutput, CancellationToken ct = default)
    {
        var segments = ResponseSegmenter.Segment(llmOutput);
        if (segments.Count == 0)
            return llmOutput;

        var sb = new System.Text.StringBuilder(llmOutput.Length);
        foreach (var seg in segments)
        {
            var current = seg.Content;
            if (_routes.TryGetValue(seg.Kind, out var plugins))
            {
                foreach (var plugin in plugins)
                {
                    seg.RoutedTo = plugin.Name;
                    var copy = new ResponseSegment
                    {
                        Kind = seg.Kind,
                        Content = current,
                        StartIndex = seg.StartIndex,
                        Length = seg.Length,
                        Language = seg.Language,
                        RoutedTo = seg.RoutedTo,
                    };
                    current = await plugin.HandleAsync(copy, ct);
                }
            }
            sb.Append(Render(seg, current));
        }
        return sb.ToString();
    }

    /// <summary>段 → 原文形态 (代码段补回围栏, 语言保留)</summary>
    private static string Render(ResponseSegment seg, string content) => seg.Kind switch
    {
        SegmentKind.Code => $"```{seg.Language ?? ""}\n{content.TrimEnd()}\n```",
        SegmentKind.InlineCode => $"`{content}`",
        _ => content,
    };
}
