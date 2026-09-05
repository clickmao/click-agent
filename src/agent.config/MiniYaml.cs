using System.Globalization;
using System.Text;

namespace agent.config;

/// <summary>
/// 极简 YAML 子集解析器 (零反射, NativeAOT 安全) — 全框架配置读取的地基。
/// 支持特性 (《全模块 YAML 配置开发规范》实际使用的子集):
///   - 2 空格缩进的嵌套映射 (dict)
///   - 标量: string / int / long / double / bool(true|false) / null(空值)
///   - "- " 开头的列表项 (列表元素为标量或嵌套映射)
///   - # 注释 (整行 + 行尾) 与空行
/// 不支持 (规范禁止或未用): 锚点/别名、多行块 |&gt;、流式 {} []、Tab 缩进、引号内 #。
/// 引号 ("..." / '...') 仅在字符串首尾成对出现时剥离 (保留内部内容原样)。
/// 输出: Dictionary&lt;string, object?&gt; / List&lt;object?&gt; / 标量。
/// </summary>
public static class MiniYaml
{
    public static Dictionary<string, object?> Parse(string yamlText)
    {
        var lines = Preprocess(yamlText);
        var pos = 0;
        var root = ParseDict(lines, ref pos, indentLevel: 0);
        return root;
    }

    private static Dictionary<string, object?> ParseDict(List<(int Indent, string Text)> lines, ref int pos, int indentLevel)
    {
        var dict = new Dictionary<string, object?>();
        int? blockIndent = null;
        while (pos < lines.Count)
        {
            var (indent, text) = lines[pos];
            if (indent < indentLevel) break;
            if (indent > indentLevel) throw new FormatException($"MiniYaml: 意外的缩进 (行 {pos + 1}: '{text}')");

            blockIndent ??= indent;
            if (text.StartsWith("- ", StringComparison.Ordinal) || text == "-")
            {
                // 映射节点下的列表是非法结构 (列表须挂在 key 下) — 防御性报错
                throw new FormatException($"MiniYaml: 映射内出现裸列表项 (行 {pos + 1}: '{text}')");
            }

            var sep = text.IndexOf(':');
            if (sep <= 0) throw new FormatException($"MiniYaml: 缺少 key: 分隔 (行 {pos + 1}: '{text}')");
            var key = Unquote(text[..sep].Trim());
            var rest = text[(sep + 1)..].Trim();

            if (rest.Length == 0)
            {
                // 嵌套节点: 看下一行缩进决定是 dict 还是 list
                pos++;
                if (pos < lines.Count && lines[pos].Indent > indent)
                {
                    if (IsListLine(lines[pos].Text))
                        dict[key] = ParseList(lines, ref pos, lines[pos].Indent);
                    else
                        dict[key] = ParseDict(lines, ref pos, lines[pos].Indent);
                }
                else
                {
                    dict[key] = null; // 空值节点
                }
            }
            else if (IsListLine(rest))
            {
                // 行内列表头 (key: 后直接跟 - 项的写法不支持, 规范禁止行内数组)
                throw new FormatException($"MiniYaml: key 后跟列表项不支持 (行 {pos + 1}: '{text}')");
            }
            else
            {
                dict[key] = ParseScalar(rest);
                pos++;
            }
        }
        return dict;
    }

    private static List<object?> ParseList(List<(int Indent, string Text)> lines, ref int pos, int indentLevel)
    {
        var list = new List<object?>();
        while (pos < lines.Count)
        {
            var (indent, text) = lines[pos];
            if (indent < indentLevel) break;
            if (indent > indentLevel) throw new FormatException($"MiniYaml: 列表项缩进异常 (行 {pos + 1}: '{text}')");
            if (!IsListLine(text)) break;

            var item = text[2..].Trim();
            if (item.Length == 0)
            {
                // "- " 后空: 下一行更深缩进开始的映射作为元素
                pos++;
                if (pos < lines.Count && lines[pos].Indent > indent)
                    list.Add(ParseDict(lines, ref pos, lines[pos].Indent));
                else
                    list.Add(null);
            }
            else if (item.Contains(':'))
            {
                // "- k: v" 开头的映射元素: 首键来自本行 "- " 后内容,
                // 后续行首缩进 > 本行行首缩进的键都并入同一元素 (映射后续键)
                var elem = new Dictionary<string, object?>();
                var sep = item.IndexOf(':');
                var k = Unquote(item[..sep].Trim());
                var rest = item[(sep + 1)..].Trim();
                elem[k] = rest.Length == 0 ? null : ParseScalar(rest);
                pos++;
                // 吞并属于该元素的后续键 (缩进更深或同深且非列表行 — 同深也属于: "- a: 1" 后
                // "  b: 2" 的行首缩进 = 行首+2 > 行首)
                while (pos < lines.Count && lines[pos].Indent > indent && !IsListLine(lines[pos].Text))
                {
                    var (i2, t2) = lines[pos];
                    var s2 = t2.IndexOf(':');
                    if (s2 <= 0) throw new FormatException($"MiniYaml: 列表映射元素内缺少 key: (行 {pos + 1}: '{t2}')");
                    var r2 = t2[(s2 + 1)..].Trim();
                    elem[Unquote(t2[..s2].Trim())] = r2.Length == 0 ? null : ParseScalar(r2);
                    pos++;
                }
                list.Add(elem);
            }
            else
            {
                list.Add(ParseScalar(item));
                pos++;
            }
        }
        return list;
    }

    private static bool IsListLine(string text) =>
        text.StartsWith("- ", StringComparison.Ordinal) || text == "-";

    private static object? ParseScalar(string raw)
    {
        var s = Unquote(raw.Trim());
        if (s.Length == 0 || s == "null" || s == "~") return null;
        if (s == "true") return true;
        if (s == "false") return false;
        // 数字: int/long
        if (long.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var l)) return l;
        // 浮点 (含科学计数)
        if (double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d)) return d;
        return s;
    }

    private static string Unquote(string s)
    {
        if (s.Length >= 2)
        {
            var first = s[0];
            var last = s[^1];
            if ((first == '"' && last == '"') || (first == '\'' && last == '\''))
                return s[1..^1];
        }
        return s;
    }

    private static List<(int Indent, string Text)> Preprocess(string yamlText)
    {
        var result = new List<(int, string)>();
        var rawLines = yamlText.Replace("\r\n", "\n").Split('\n');
        foreach (var raw in rawLines)
        {
            // 整行注释/空行跳过
            var noComment = StripComment(raw);
            if (noComment.Trim().Length == 0) continue;
            if (noComment.Contains('\t')) throw new FormatException("MiniYaml: 禁止 Tab 缩进 (规范 4.4)");
            var indent = CountIndent(noComment);
            var text = noComment.TrimEnd();
            result.Add((indent, text.Trim()));
        }
        return result;
    }

    private static string StripComment(string line)
    {
        // 引号外第一个 # 起为注释 (简单状态机, 引号不成对则视为无注释行尾)
        var inQuote = false;
        var quoteChar = '"';
        var sb = new StringBuilder();
        foreach (var ch in line)
        {
            if (inQuote)
            {
                if (ch == quoteChar) inQuote = false;
            }
            else if (ch == '"' || ch == '\'')
            {
                inQuote = true;
                quoteChar = ch;
            }
            else if (ch == '#')
            {
                break;
            }
            sb.Append(ch);
        }
        return sb.ToString();
    }

    private static int CountIndent(string line)
    {
        var i = 0;
        while (i < line.Length && line[i] == ' ') i++;
        return i;
    }
}
