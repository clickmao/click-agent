using System.Text.RegularExpressions;

namespace agent.registry;


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

    /// <summary>
    /// R374 (D3): 聚合各插件的**产物校验结论** (主链据此回流修复)。
    /// 契约: 取即清 (drain) — 结论只被消费一次, 避免同一失败被反复"修复"。
    /// </summary>
    public IReadOnlyList<ArtifactCheck> DrainArtifactChecks()
    {
        List<ArtifactCheck>? all = null;
        foreach (var p in _plugins)
        {
            if (p is not IArtifactCheckSource src) continue;
            var items = src.DrainNewChecks();
            if (items.Count == 0) continue;
            (all ??= new List<ArtifactCheck>()).AddRange(items);
        }
        return (IReadOnlyList<ArtifactCheck>?)all ?? Array.Empty<ArtifactCheck>();
    }

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
