using System.Text;

namespace agent.rover.token;

/// <summary>
/// Jinja 渲染环境选项。默认值由 R406 探针 (scripts/r406_jinja_env_probe.py) 用存档模板 + 金标夹具**枚举反解**得出:
/// 唯一同时满足三套夹具 (deepseek 12/12, r1 10/10, qwen25-math 10/10) 的组合是
/// TrimBlocks=false, LStripBlocks=false, KeepTrailingNewline=true。
/// 反证: qwen25-math 模板在 TrimBlocks=true 时 0/10 (末行 '\n' 被吞), 在 KeepTrailingNewline=false 时 0/10。
/// 注意: `eval/rover/tokref/chat_golden.jsonl` 的 env_options 字段标注 trim_blocks=True 与实测不符 (该模板对两开关不敏感,
/// 故标注从未被证伪) —— 以探针结论为准, 不以标注为准。
/// </summary>
public sealed record JinjaOptions
{
    /// <summary>夹具反解出的唯一解 (见类型注释)。</summary>
    public static readonly JinjaOptions Default = new();

    /// <summary>true = 删除块标签 `%}` 之后的第一个换行。</summary>
    public bool TrimBlocks { get; init; }

    /// <summary>true = 删除块标签所在行首的空白缩进。</summary>
    public bool LStripBlocks { get; init; }

    /// <summary>true = 保留模板源末尾的换行 (jinja 默认 false)。</summary>
    public bool KeepTrailingNewline { get; init; } = true;

    /// <summary>显式 `{%- -%}` / `{{- -}}` 不受这些开关影响, 始终生效。</summary>
    public static JinjaOptions JinjaDefault => new() { KeepTrailingNewline = false };
}

/// <summary>
/// Jinja **子集**解释器 (R406 P0-2 / R403 续作): 从 GGUF 的 `tokenizer.chat_template` 原文渲染, 不写死任何模型。
///
/// 已实现 (经三套夹具 32 例逐字节验收):
///   语句   if/elif/else/endif, for/else/endfor (含 loop.first/index0/last/length), set (=, 含 ns.attr =),
///          `{%- -%}`/`{{- -}}` 空白控制, trim_blocks/lstrip_blocks/keep_trailing_newline
///   表达式 字面量 (str/int/float/bool/none), 下标 (含负下标), 属性, 方法与函数调用 (split/namespace/range 等),
///          过滤器 (tojson/trim/length/...), 算术 (+ - * / // % ~), 比较 (== != < <= > >=), and/or/not,
///          in / not in, is defined / is none / is not none / is true / is false / is string / is number / is iterable
///   语义   宽松 Undefined (假值, 渲染空串, 取属性仍为 Undefined), namespace() 可跨循环写回, for 每次迭代独立作用域,
///          and/or 返回操作数 (python 语义)
/// 未实现 (走到即抛 <see cref="JinjaUnsupportedException"/>, **不静默降级**):
///          macro/import/include/call/filter-block/raw, 多目标解包 for, dict 字面量, 三元 if-else, `|` 过滤器带参数,
///          未知过滤器/方法/测试名, jinja 全局函数 (range 之外)
/// </summary>
public static class JinjaTemplate
{
    /// <summary>渲染模板。context 必须是 dict/namespace (模板顶层 `{% set %}` 写入本层作用域, 不回写 context)。</summary>
    public static string Render(string template, JinjaValue context, JinjaOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(template);
        JinjaOptions opt = options ?? JinjaOptions.Default;
        string source = template;
        if (!opt.KeepTrailingNewline)
        {
            if (source.EndsWith("\r\n", StringComparison.Ordinal)) source = source[..^2];
            else if (source.EndsWith('\n')) source = source[..^1];
        }

        List<TplToken> tokens = Tokenize(source, opt);
        int cursor = 0;
        List<TplNode> body = ParseNodes(tokens, ref cursor, null);
        if (cursor != tokens.Count)
        {
            throw new JinjaEvaluationException($"模板结构不匹配: 多余的结束标签 '{tokens[cursor].Text}'");
        }

        JinjaScope scope = new(null);
        if (context is not null && !context.IsUndefined && !context.IsNull)
        {
            IReadOnlyDictionary<string, JinjaValue>? fields = context.Fields;
            if (fields is null)
            {
                throw new JinjaEvaluationException($"模板上下文必须是 dict/namespace, 实际 {context.Kind}");
            }

            foreach (KeyValuePair<string, JinjaValue> kv in fields)
            {
                scope.Set(kv.Key, kv.Value);
            }
        }

        StringBuilder sb = new(source.Length + 64);
        RenderNodes(body, scope, sb);
        return sb.ToString();
    }

    // ---------------------------------------------------------------- 词法 (模板层)

    private enum TplKind
    {
        Text,
        Output,
        Statement,
    }

    private readonly record struct TplToken(TplKind Kind, string Text);

    private static List<TplToken> Tokenize(string s, JinjaOptions o)
    {
        List<TplToken> list = [];
        int i = 0;
        while (i < s.Length)
        {
            int at = FirstTag(s, i);
            if (at < 0)
            {
                AppendText(list, s[i..]);
                break;
            }

            string kind = s.Substring(at, 2);
            string before = s[i..at];
            bool dashLeft = at + 2 < s.Length && s[at + 2] == '-';
            if (dashLeft)
            {
                before = before.TrimEnd();
            }
            else if (kind == "{%" && o.LStripBlocks)
            {
                before = StripLineIndent(before);
            }

            AppendText(list, before);

            string close = kind switch { "{{" => "}}", "{%" => "%}", _ => "#}" };
            int end = s.IndexOf(close, at + 2, StringComparison.Ordinal);
            if (end < 0)
            {
                throw new JinjaEvaluationException($"模板标签未闭合: {kind} @{at}");
            }

            string inner = s[(at + 2)..end];
            if (inner.StartsWith('-')) inner = inner[1..];
            bool dashRight = inner.EndsWith('-');
            if (dashRight) inner = inner[..^1];

            if (kind == "{{")
            {
                list.Add(new TplToken(TplKind.Output, inner.Trim()));
            }
            else if (kind == "{%")
            {
                list.Add(new TplToken(TplKind.Statement, inner.Trim()));
            }

            i = end + close.Length;
            if (dashRight)
            {
                while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
            }
            else if (kind == "{%" && o.TrimBlocks)
            {
                if (i < s.Length && s[i] == '\r') i++;
                if (i < s.Length && s[i] == '\n') i++;
            }
        }

        return list;
    }

    private static int FirstTag(string s, int from)
    {
        int best = -1;
        foreach (string tag in TagOpens)
        {
            int idx = s.IndexOf(tag, from, StringComparison.Ordinal);
            if (idx >= 0 && (best < 0 || idx < best)) best = idx;
        }

        return best;
    }

    private static readonly string[] TagOpens = ["{{", "{%", "{#"];

    private static void AppendText(List<TplToken> list, string text)
    {
        if (text.Length == 0) return;
        if (list.Count > 0 && list[^1].Kind == TplKind.Text)
        {
            list[^1] = list[^1] with { Text = list[^1].Text + text };
            return;
        }

        list.Add(new TplToken(TplKind.Text, text));
    }

    /// <summary>lstrip_blocks: 若标签前的文本自上一个换行以来仅为空格/制表符, 则删掉这段缩进。</summary>
    private static string StripLineIndent(string before)
    {
        int nl = before.LastIndexOf('\n');
        string tail = nl < 0 ? before : before[(nl + 1)..];
        for (int k = 0; k < tail.Length; k++)
        {
            if (tail[k] is not (' ' or '\t')) return before;
        }

        return nl < 0 ? string.Empty : before[..(nl + 1)];
    }

    // ---------------------------------------------------------------- 语法树

    private abstract class TplNode;

    private sealed class TplText(string text) : TplNode
    {
        public string Text { get; } = text;
    }

    private sealed class TplOutput(JinjaExpr expr) : TplNode
    {
        public JinjaExpr Expr { get; } = expr;
    }

    private sealed class TplIf(List<(JinjaExpr Cond, List<TplNode> Body)> branches, List<TplNode>? elseBody) : TplNode
    {
        public List<(JinjaExpr Cond, List<TplNode> Body)> Branches { get; } = branches;

        public List<TplNode>? ElseBody { get; } = elseBody;
    }

    private sealed class TplFor(string target, JinjaExpr seq, List<TplNode> body, List<TplNode>? elseBody, string stmt) : TplNode
    {
        public string Target { get; } = target;

        public JinjaExpr Seq { get; } = seq;

        public List<TplNode> Body { get; } = body;

        public List<TplNode>? ElseBody { get; } = elseBody;

        public string Stmt { get; } = stmt;
    }

    private sealed class TplSet(string name, string? attr, JinjaExpr value) : TplNode
    {
        public string Name { get; } = name;

        public string? Attr { get; } = attr;

        public JinjaExpr Value { get; } = value;
    }

    private sealed class TplUnsupported(string stmt) : TplNode
    {
        public string Stmt { get; } = stmt;
    }

    private static readonly string[] IfStops = ["elif", "else", "endif"];

    private static readonly string[] ForStops = ["else", "endfor"];

    private static List<TplNode> ParseNodes(List<TplToken> tokens, ref int cursor, string[]? stops)
    {
        List<TplNode> body = [];
        while (cursor < tokens.Count)
        {
            TplToken tok = tokens[cursor];
            if (tok.Kind == TplKind.Text)
            {
                body.Add(new TplText(tok.Text));
                cursor++;
                continue;
            }

            if (tok.Kind == TplKind.Output)
            {
                body.Add(new TplOutput(JinjaExprParser.Parse(tok.Text)));
                cursor++;
                continue;
            }

            string head = FirstWord(tok.Text);
            if (stops is not null && Array.IndexOf(stops, head) >= 0) return body;

            cursor++;
            switch (head)
            {
                case "if":
                    body.Add(ParseIf(tokens, ref cursor, Rest(tok.Text, "if")));
                    break;
                case "for":
                    body.Add(ParseFor(tokens, ref cursor, tok.Text));
                    break;
                case "set":
                    body.Add(ParseSet(tok.Text));
                    break;
                default:
                    if (IsClosingKeyword(head))
                    {
                        throw new JinjaEvaluationException($"多余的结束标签 '{head}' (无匹配的开块): '{tok.Text}'");
                    }

                    if (IsOpenKeyword(head))
                    {
                        // 成块关键字 (macro/block/call/...) 未实现: 跳过整块后合成**单个**未实现节点,
                        // 报告一次且不误报「多余结束标签」(cursor 已消费开标签)。
                        string endKw = "end" + head;
                        int depth = 1;
                        while (cursor < tokens.Count && depth > 0)
                        {
                            if (tokens[cursor].Kind == TplKind.Statement)
                            {
                                string inner = FirstWord(tokens[cursor].Text);
                                if (inner == head) depth++;
                                else if (inner == endKw) depth--;
                            }

                            cursor++;
                        }

                        if (depth > 0) throw new JinjaEvaluationException($"'{head}' 块未闭合 (缺 {endKw})");
                        body.Add(new TplUnsupported($"{tok.Text} … {endKw}"));
                        break;
                    }

                    body.Add(new TplUnsupported(tok.Text));
                    break;
            }
        }

        return body;
    }

    private static TplNode ParseIf(List<TplToken> tokens, ref int cursor, string firstExpr)
    {
        List<(JinjaExpr, List<TplNode>)> branches = [];
        branches.Add((JinjaExprParser.Parse(firstExpr), ParseNodes(tokens, ref cursor, IfStops)));
        List<TplNode>? elseBody = null;
        while (true)
        {
            if (cursor >= tokens.Count) throw new JinjaEvaluationException("{% if %} 未闭合 (缺 endif)");
            string head = FirstWord(tokens[cursor].Text);
            if (head == "elif")
            {
                string expr = Rest(tokens[cursor].Text, "elif");
                cursor++;
                branches.Add((JinjaExprParser.Parse(expr), ParseNodes(tokens, ref cursor, IfStops)));
                continue;
            }

            if (head == "else")
            {
                cursor++;
                elseBody = ParseNodes(tokens, ref cursor, ["endif"]);
            }

            if (cursor >= tokens.Count || FirstWord(tokens[cursor].Text) != "endif")
            {
                throw new JinjaEvaluationException("{% if %} 未闭合 (缺 endif)");
            }

            cursor++;
            break;
        }

        return new TplIf(branches, elseBody);
    }

    private static TplNode ParseFor(List<TplToken> tokens, ref int cursor, string stmt)
    {
        string spec = Rest(stmt, "for").Trim();
        int inIdx = IndexOfTopLevelKeyword(spec, "in");
        if (inIdx < 0) throw new JinjaEvaluationException($"for 语句缺少 in: '{stmt}'");
        string target = spec[..inIdx].Trim();
        string seqText = spec[(inIdx + 2)..].Trim();
        if (target.Length == 0 || seqText.Length == 0) throw new JinjaEvaluationException($"for 语句不完整: '{stmt}'");
        if (target.Contains(',')) throw new JinjaUnsupportedException($"for 多目标解包未实现: '{stmt}'");
        if (!IsIdentifier(target)) throw new JinjaUnsupportedException($"for 迭代目标非简单标识符: '{stmt}'");

        JinjaExpr seq = JinjaExprParser.Parse(seqText);
        List<TplNode> body = ParseNodes(tokens, ref cursor, ForStops);
        List<TplNode>? elseBody = null;
        if (cursor < tokens.Count && FirstWord(tokens[cursor].Text) == "else")
        {
            cursor++;
            elseBody = ParseNodes(tokens, ref cursor, ["endfor"]);
        }

        if (cursor >= tokens.Count || FirstWord(tokens[cursor].Text) != "endfor")
        {
            throw new JinjaEvaluationException("{% for %} 未闭合 (缺 endfor)");
        }

        cursor++;
        return new TplFor(target, seq, body, elseBody, stmt);
    }

    private static TplNode ParseSet(string stmt)
    {
        string spec = Rest(stmt, "set").Trim();
        int eq = IndexOfTopLevelChar(spec, '=');
        if (eq < 0) throw new JinjaEvaluationException($"set 语句缺少 '=': '{stmt}'");
        string lhs = spec[..eq].Trim();
        string rhs = spec[(eq + 1)..].Trim();
        if (lhs.Length == 0 || rhs.Length == 0) throw new JinjaEvaluationException($"set 语句不完整: '{stmt}'");
        int dot = lhs.IndexOf('.');
        string name = dot < 0 ? lhs : lhs[..dot];
        string? attr = dot < 0 ? null : lhs[(dot + 1)..];
        if (!IsIdentifier(name)) throw new JinjaUnsupportedException($"set 目标非简单标识符: '{stmt}'");
        if (attr is not null && !IsIdentifier(attr)) throw new JinjaUnsupportedException($"set 属性名非法 (仅支持 ns.attr): '{stmt}'");

        return new TplSet(name, attr, JinjaExprParser.Parse(rhs));
    }

    // ---------------------------------------------------------------- 渲染

    private static void RenderNodes(List<TplNode> nodes, JinjaScope scope, StringBuilder sb)
    {
        foreach (TplNode node in nodes)
        {
            switch (node)
            {
                case TplText text:
                    sb.Append(text.Text);
                    break;
                case TplOutput output:
                    sb.Append(output.Expr.Eval(scope).Display());
                    break;
                case TplIf branch:
                    {
                        bool taken = false;
                        foreach ((JinjaExpr cond, List<TplNode> body) in branch.Branches)
                        {
                            if (cond.Eval(scope).Truthy())
                            {
                                RenderNodes(body, scope, sb);
                                taken = true;
                                break;
                            }
                        }

                        if (!taken && branch.ElseBody is not null) RenderNodes(branch.ElseBody, scope, sb);
                        break;
                    }

                case TplFor loop:
                    RenderFor(loop, scope, sb);
                    break;
                case TplSet set:
                    {
                        JinjaValue value = set.Value.Eval(scope);
                        if (set.Attr is null)
                        {
                            scope.Set(set.Name, value);
                            break;
                        }

                        JinjaValue target = scope.Get(set.Name);
                        if (target.IsUndefined || target.Fields is null)
                        {
                            throw new JinjaEvaluationException($"set {set.Name}.{set.Attr}: '{set.Name}' 不是 namespace/dict (实际 {target.Kind})");
                        }

                        target.SetField(set.Attr, value);
                        break;
                    }

                case TplUnsupported unsupported:
                    throw new JinjaUnsupportedException($"模板语句未实现: '{{% {unsupported.Stmt} %}}'");
                default:
                    throw new JinjaUnsupportedException($"模板节点未实现: {node.GetType().Name}");
            }
        }
    }

    private static void RenderFor(TplFor loop, JinjaScope scope, StringBuilder sb)
    {
        JinjaValue seq = loop.Seq.Eval(scope);
        List<JinjaValue> items = Iterate(seq, loop.Stmt);
        if (items.Count == 0)
        {
            if (loop.ElseBody is not null) RenderNodes(loop.ElseBody, scope, sb);
            return;
        }

        int index = 0;
        foreach (JinjaValue item in items)
        {
            JinjaScope iteration = scope.Child();
            iteration.Set(loop.Target, item);
            Dictionary<string, JinjaValue> loopInfo = new(StringComparer.Ordinal)
            {
                ["index0"] = JinjaValue.Of((long)index),
                ["index"] = JinjaValue.Of((long)index + 1),
                ["first"] = JinjaValue.Of(index == 0),
                ["last"] = JinjaValue.Of(index == items.Count - 1),
                ["length"] = JinjaValue.Of((long)items.Count),
                ["revindex"] = JinjaValue.Of((long)(items.Count - index)),
                ["revindex0"] = JinjaValue.Of((long)(items.Count - index - 1)),
            };
            iteration.Set("loop", JinjaValue.Dict(loopInfo));
            RenderNodes(loop.Body, iteration, sb);
            index++;
        }
    }

    private static List<JinjaValue> Iterate(JinjaValue seq, string stmt)
    {
        switch (seq.Kind)
        {
            case JinjaKind.List:
                return [.. seq.Items];
            case JinjaKind.Dict:
            case JinjaKind.Namespace:
                {
                    List<JinjaValue> keys = [];
                    foreach (string key in seq.Fields!.Keys) keys.Add(JinjaValue.Of(key));
                    return keys;
                }

            case JinjaKind.Str:
                {
                    List<JinjaValue> chars = [];
                    foreach (char c in seq.AsString) chars.Add(JinjaValue.Of(c.ToString()));
                    return chars;
                }

            case JinjaKind.Undefined:
            case JinjaKind.Null:
                throw new JinjaEvaluationException($"for 目标未定义/为空, 不可迭代: '{stmt}' (jinja 宽松模式同样报错; 模板须先判 defined)");
            default:
                throw new JinjaEvaluationException($"for 目标不可迭代: {seq.Kind} ('{stmt}')");
        }
    }

    // ---------------------------------------------------------------- 小工具

    private static bool IsOpenKeyword(string head) =>
        head is "macro" or "block" or "call" or "filter" or "with" or "raw" or "trans" or "autoescape";

    private static bool IsClosingKeyword(string head) =>
        head is "endif" or "endfor" or "endraw" or "endmacro" or "endblock" or "endfilter" or "endwith"
            or "endcall" or "endtrans" or "else" or "elif";

    private static string FirstWord(string stmt)
    {
        ReadOnlySpan<char> span = stmt.AsSpan().TrimStart();
        int k = 0;
        while (k < span.Length && (char.IsLetterOrDigit(span[k]) || span[k] == '_')) k++;
        return span[..k].ToString();
    }

    private static string Rest(string stmt, string keyword) => stmt.TrimStart()[keyword.Length..];

    private static bool IsIdentifier(string s)
    {
        if (s.Length == 0) return false;
        if (!char.IsLetter(s[0]) && s[0] != '_') return false;
        for (int k = 1; k < s.Length; k++)
        {
            if (!char.IsLetterOrDigit(s[k]) && s[k] != '_') return false;
        }

        return true;
    }

    /// <summary>在顶层 (跳过引号与括号内) 找关键字, 返回其后首个非空白位置前的下标; 未找到返回 -1。</summary>
    private static int IndexOfTopLevelKeyword(string text, string keyword)
    {
        int depth = 0;
        char quote = '\0';
        for (int k = 0; k + keyword.Length <= text.Length; k++)
        {
            char c = text[k];
            if (quote != '\0')
            {
                if (c == '\\') { k++; continue; }
                if (c == quote) quote = '\0';
                continue;
            }

            if (c is '\'' or '"') { quote = c; continue; }
            if (c is '(' or '[' or '{') { depth++; continue; }
            if (c is ')' or ']' or '}') { depth--; continue; }
            if (depth != 0) continue;
            if (!IsWordAt(text, k, keyword)) continue;
            return k;
        }

        return -1;
    }

    private static bool IsWordAt(string text, int at, string word)
    {
        if (at + word.Length > text.Length) return false;
        if (string.CompareOrdinal(text, at, word, 0, word.Length) != 0) return false;
        bool leftOk = at == 0 || !(char.IsLetterOrDigit(text[at - 1]) || text[at - 1] == '_');
        int after = at + word.Length;
        bool rightOk = after >= text.Length || !(char.IsLetterOrDigit(text[after]) || text[after] == '_');
        return leftOk && rightOk;
    }

    /// <summary>在顶层找字符 (跳过引号与括号内), 且不把 `==`/`!=`/`&lt;=` 等算作命中。</summary>
    private static int IndexOfTopLevelChar(string text, char target)
    {
        int depth = 0;
        char quote = '\0';
        for (int k = 0; k < text.Length; k++)
        {
            char c = text[k];
            if (quote != '\0')
            {
                if (c == '\\') { k++; continue; }
                if (c == quote) quote = '\0';
                continue;
            }

            if (c is '\'' or '"') { quote = c; continue; }
            if (c is '(' or '[' or '{') { depth++; continue; }
            if (c is ')' or ']' or '}') { depth--; continue; }
            if (depth != 0 || c != target) continue;
            char prev = k > 0 ? text[k - 1] : '\0';
            char next = k + 1 < text.Length ? text[k + 1] : '\0';
            if (target == '=' && (prev is '=' or '!' or '<' or '>' || next == '=')) continue;
            return k;
        }

        return -1;
    }
}
