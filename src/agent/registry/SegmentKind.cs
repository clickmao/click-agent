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

    /// <summary>R371 D4-b: 是否由**启发式提升**而来 (无围栏) — 供真机 KPI 归因 (fenced vs heuristic)。</summary>
    public bool Promoted { get; set; }

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
        var segments = SegmentFenced(text);
        // R371 D4-b: 模型未给围栏时 (输出纪律不可靠, 真机 3 次仅 1 次带围栏) → 用**保守启发式**识别整段代码,
        // 否则 artifact 链(落盘/编译/运行)永不触发。原则: 宁可不提升, 不可误判 (误判会把散文当代码落盘)。
        if (!segments.Exists(s => s.Kind == SegmentKind.Code))
        {
            var run = FindCodeRun(text);
            if (run is { } r)
                return RebuildWithCode(text, r.start, r.length, r.lang);
        }
        return segments;
    }

    /// <summary>最小可提升代码段: ≥8 行代码行 / ≥200 字符。</summary>
    private const int MinCodeLines = 8;
    private const int MinCodeChars = 200;

    /// <summary>
    /// 保守的"整段代码"定位: 从**首个代码行**起, 到**最后一个代码行或中性行(空行/注释/文档串)**止,
    /// 中间允许注释/空行/文档串 (不打断), 但散文行占比不得超过 35%。不满足即放弃 (返回 null)。
    /// </summary>
    private static (int start, int length, string? lang)? FindCodeRun(string text)
    {
        var lines = SplitLines(text);
        var first = -1;
        for (var i = 0; i < lines.Count; i++)
        {
            if (lines[i].code) { first = i; break; }
        }
        if (first < 0) return null;

        // 段尾只认"最后一个代码行 + 紧接其后的空行/注释" —— 一旦出现散文, 该候选作废 (散文后置不得并入)。
        var lastCode = -1;
        var codeLines = 0;
        var proseAfterCode = false;
        var neutralEnd = -1;
        for (var i = first; i < lines.Count; i++)
        {
            if (lines[i].code)
            {
                codeLines++;
                lastCode = i;
                proseAfterCode = false;
                neutralEnd = -1;
            }
            else if (lines[i].neutral)
            {
                if (!proseAfterCode)
                    neutralEnd = lines[i].start + lines[i].length;
            }
            else
            {
                proseAfterCode = true;   // 散文出现 (此后中性行不再延长段尾)
                neutralEnd = -1;
            }
        }
        if (lastCode < first || codeLines < MinCodeLines) return null;

        // 段**内部**的散文 (如文档串正文) 占比过高 → 放弃 (宁可漏提升, 不可误判)
        var interiorProse = 0;
        for (var i = first; i < lastCode; i++)
        {
            if (!lines[i].code && !lines[i].neutral) interiorProse++;
        }
        var nonBlank = codeLines + interiorProse;
        if (nonBlank <= 0 || interiorProse * 100 / nonBlank > 35) return null;

        var start = lines[first].start;
        var end = neutralEnd > 0 ? neutralEnd : lines[lastCode].start + lines[lastCode].length;
        while (end > start && (text[end - 1] == '\n' || text[end - 1] == '\r')) end--;
        var length = end - start;
        if (length < MinCodeChars) return null;

        return (start, length, SniffLanguage(text.Substring(start, length)));
    }

    /// <summary>语言嗅探 (仅用于给插件做路由, 判错不影响文本本身)。</summary>
    private static string? SniffLanguage(string code)
    {
        if (Regex.IsMatch(code, "(?m)^\\s*(?:import |from |def |class )") ||
            code.Contains("#!/usr/bin/env python", StringComparison.Ordinal) ||
            code.Contains("\nprint(", StringComparison.Ordinal) ||
            code.Contains("self.", StringComparison.Ordinal))
            return "python";
        if (Regex.IsMatch(code, "(?m)^\\s*(?:using |namespace |public (?:sealed )?class |internal (?:sealed )?class )"))
            return "csharp";
        return null;
    }

    private static List<ResponseSegment> RebuildWithCode(string text, int start, int length, string? lang)
    {
        var segments = new List<ResponseSegment>();
        if (start > 0) AddTextWithInline(segments, text, 0, start);
        segments.Add(new ResponseSegment
        {
            Kind = SegmentKind.Code,
            Content = text.Substring(start, length),
            StartIndex = start,
            Length = length,
            Language = lang,
            Promoted = true,   // R371 D4-b: 真机归因用 (fenced vs 启发式提升) — KPI 必须能归因到机制
        });
        var rest = start + length;
        if (rest < text.Length) AddTextWithInline(segments, text, rest, text.Length - rest);
        return segments;
    }

    /// <summary>行分类: Code(像代码) / Neutral(空行·整行注释·文档串标记, 不打断代码段) / Prose(散文)。</summary>
    private static List<(int start, int length, bool code, bool neutral)> SplitLines(string text)
    {
        var lines = new List<(int, int, bool, bool)>();
        var i = 0;
        var inTripleQuote = false;   // R371 D4-b v2: 字符串字面量状态 (行级, 三引号计数奇偶翻转)
        while (i <= text.Length)
        {
            var nl = text.IndexOf('\n', i);
            var end = nl < 0 ? text.Length : nl;
            var lineLen = end - i;
            var t = text.Substring(i, lineLen).Trim();
            var code = !inTripleQuote && LooksLikeCode(t);
            // R371 D4-b v2 (真机 RUN3 实证): **三引号字符串内部的行不是散文** ——
            // 中文 docstring 让"散文占比"虚高 (run3 优质 Python 因文档健全被判 47% 散文 → 放弃提升, artifact 命中 0)。
            // 按三引号开关把串内行记为中性; 串内即使"看起来像代码"也不算代码行 (示例代码在文档里)。
            var neutral = inTripleQuote
                          || t.Length == 0
                          || t.StartsWith("#", StringComparison.Ordinal) && !LooksLikeCode(t)
                          || t.StartsWith("///", StringComparison.Ordinal)
                          || t.StartsWith("\"\"\"", StringComparison.Ordinal)
                          || t.StartsWith("'''", StringComparison.Ordinal);
            lines.Add((i, lineLen, code, neutral && !code));
            // R371 D4-b v2: 按本行三引号出现次数奇偶翻转"串内"状态 (开/闭同一行则自行抵消)
            var q = CountOf(t, "\"\"\"") + CountOf(t, "'''");
            if (q % 2 == 1) inTripleQuote = !inTripleQuote;
            if (nl < 0) break;
            i = nl + 1;
        }
        return lines;
    }

    private static readonly string[] CodeKeywords =
    {
        "import ", "from ", "def ", "class ", "return", "if ", "elif ", "else", "for ", "while ",
        "try", "except", "finally", "with ", "lambda", "yield", "async ", "await ", "print(",
        "@", "#!/", "using ", "namespace ", "public ", "private ", "protected ", "internal ",
        "static ", "void ", "var ", "let ", "const ", "function ", "struct ", "enum ", "interface ",
        "#include", "package ", "func ", "module.exports", "console.log", "def(", "impl ", "fn ",
    };

    /// <summary>像代码的行: 关键词起手, 或含典型代码结构 (缩进+调用/赋值/收尾符号)。</summary>
    /// <summary>子串出现次数 (序数, 非重叠)。</summary>
    private static int CountOf(string s, string needle)
    {
        var n = 0;
        var idx = 0;
        while ((idx = s.IndexOf(needle, idx, StringComparison.Ordinal)) >= 0) { n++; idx += needle.Length; }
        return n;
    }

    private static bool LooksLikeCode(string t)
    {
        if (t.Length == 0) return false;
        foreach (var k in CodeKeywords)
        {
            if (t.StartsWith(k, StringComparison.Ordinal)) return true;
        }
        // 赋值/调用/类型标注等结构信号 (要求同时出现, 降低散文误判)
        var hasAssign = t.Contains(" = ", StringComparison.Ordinal) || t.Contains("==", StringComparison.Ordinal);
        var hasCall = t.Contains('(') && t.Contains(')');
        var endsCode = t.EndsWith(":", StringComparison.Ordinal) || t.EndsWith("{", StringComparison.Ordinal)
                       || t.EndsWith("}", StringComparison.Ordinal) || t.EndsWith(";", StringComparison.Ordinal)
                       || t.EndsWith(")", StringComparison.Ordinal);
        if (hasAssign && (endsCode || t.Contains('('))) return true;
        if (hasCall && endsCode) return true;
        if (t.Contains("self.", StringComparison.Ordinal) || t.Contains("->", StringComparison.Ordinal)) return true;
        return false;
    }

    /// <summary>围栏切分 (原实现)。</summary>
    private static List<ResponseSegment> SegmentFenced(string text)
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
