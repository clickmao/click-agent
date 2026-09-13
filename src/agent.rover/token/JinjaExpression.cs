using System.Globalization;
using System.Text;

namespace agent.rover.token;

/// <summary>模板解释器异常: 走到的构造未实现 (不静默降级 —— 与 <see cref="ChatTemplate"/> 既有契约一致)。</summary>
public sealed class JinjaUnsupportedException : NotSupportedException
{
    public JinjaUnsupportedException(string message)
        : base(message)
    {
    }
}

/// <summary>求值期错误 (未闭合块 / 未定义不可迭代 / 不可比较 / 参数错误)。</summary>
public sealed class JinjaEvaluationException : InvalidOperationException
{
    public JinjaEvaluationException(string message)
        : base(message)
    {
    }
}

/// <summary>名字作用域链 (jinja: for 体每次迭代为子作用域, if 体不建作用域)。</summary>
public sealed class JinjaScope
{
    private readonly Dictionary<string, JinjaValue> _names = new(StringComparer.Ordinal);
    private readonly JinjaScope? _parent;

    public JinjaScope(JinjaScope? parent = null) => _parent = parent;

    public JinjaScope Child() => new(this);

    public bool TryGet(string name, out JinjaValue value)
    {
        if (_names.TryGetValue(name, out JinjaValue? v))
        {
            value = v;
            return true;
        }

        if (_parent is not null)
        {
            return _parent.TryGet(name, out value);
        }

        value = JinjaValue.Undefined;
        return false;
    }

    public JinjaValue Get(string name) => TryGet(name, out JinjaValue v) ? v : JinjaValue.Undefined;

    public void Set(string name, JinjaValue value) => _names[name] = value;
}

internal enum JinjaTokenKind
{
    End,
    Name,
    Int,
    Num,
    Str,
    Punct,
    Keyword,
}

internal readonly struct JinjaToken
{
    public JinjaToken(JinjaTokenKind kind, string text, long intValue = 0, double numValue = 0)
    {
        Kind = kind;
        Text = text;
        IntValue = intValue;
        NumValue = numValue;
    }

    public JinjaTokenKind Kind { get; }

    public string Text { get; }

    public long IntValue { get; }

    public double NumValue { get; }
}

internal static class JinjaExprLexer
{
    private static readonly string[] Keywords = ["and", "or", "not", "in", "is", "if", "else", "true", "false", "none", "True", "False", "None"];

    private static readonly string[] Puncts =
    [
        "==", "!=", "<=", ">=", "//", "**", "(", ")", "[", "]", "{", "}", ".", ",", ":", "+", "-", "*", "/", "%", "~", "|", "<", ">", "=",
    ];

    public static List<JinjaToken> Tokenize(string text)
    {
        List<JinjaToken> tokens = [];
        int i = 0;
        while (i < text.Length)
        {
            char c = text[i];
            if (char.IsWhiteSpace(c))
            {
                i++;
                continue;
            }

            if (c == '\'' || c == '"')
            {
                (string s, int next) = ReadString(text, i);
                tokens.Add(new JinjaToken(JinjaTokenKind.Str, s));
                i = next;
                continue;
            }

            if (char.IsDigit(c))
            {
                int j = i;
                while (j < text.Length && char.IsDigit(text[j]))
                {
                    j++;
                }

                bool isFloat = j < text.Length && text[j] == '.' && j + 1 < text.Length && char.IsDigit(text[j + 1]);
                if (isFloat)
                {
                    while (j < text.Length && (char.IsDigit(text[j]) || text[j] == '.'))
                    {
                        j++;
                    }

                    tokens.Add(new JinjaToken(JinjaTokenKind.Num, text[i..j], numValue: double.Parse(text[i..j], CultureInfo.InvariantCulture)));
                }
                else
                {
                    tokens.Add(new JinjaToken(JinjaTokenKind.Int, text[i..j], long.Parse(text[i..j], CultureInfo.InvariantCulture)));
                }

                i = j;
                continue;
            }

            if (char.IsLetter(c) || c == '_')
            {
                int j = i;
                while (j < text.Length && (char.IsLetterOrDigit(text[j]) || text[j] == '_'))
                {
                    j++;
                }

                string word = text[i..j];
                tokens.Add(new JinjaToken(Array.IndexOf(Keywords, word) >= 0 ? JinjaTokenKind.Keyword : JinjaTokenKind.Name, word));
                i = j;
                continue;
            }

            string? punct = null;
            foreach (string p in Puncts)
            {
                if (string.CompareOrdinal(text, i, p, 0, p.Length) == 0)
                {
                    punct = p;
                    break;
                }
            }

            if (punct is null)
            {
                throw new JinjaUnsupportedException($"表达式含不支持的字符 '{c}' (上下文: {Snippet(text, i)})");
            }

            tokens.Add(new JinjaToken(JinjaTokenKind.Punct, punct));
            i += punct.Length;
        }

        tokens.Add(new JinjaToken(JinjaTokenKind.End, string.Empty));
        return tokens;
    }

    private static (string Value, int Next) ReadString(string text, int start)
    {
        char quote = text[start];
        StringBuilder sb = new();
        int i = start + 1;
        while (i < text.Length)
        {
            char c = text[i];
            if (c == quote)
            {
                return (sb.ToString(), i + 1);
            }

            if (c == '\\' && i + 1 < text.Length)
            {
                char e = text[i + 1];
                sb.Append(e switch
                {
                    'n' => '\n',
                    't' => '\t',
                    'r' => '\r',
                    '0' => '\0',
                    '\\' => '\\',
                    '\'' => '\'',
                    '"' => '"',
                    _ => '\\',
                });
                if (e is not ('n' or 't' or 'r' or '0' or '\\' or '\'' or '"'))
                {
                    sb.Append(e);
                }

                i += 2;
                continue;
            }

            sb.Append(c);
            i++;
        }

        throw new JinjaEvaluationException($"字符串字面量未闭合: {Snippet(text, start)}");
    }

    internal static string Snippet(string text, int at)
    {
        int lo = Math.Max(0, at - 20);
        int hi = Math.Min(text.Length, at + 20);
        return text[lo..hi].ReplaceLineEndings("\\n");
    }
}

/// <summary>Jinja 表达式 AST。Eval 失败一律抛异常 —— 不求值成「空字符串」这种静默降级。</summary>
public abstract class JinjaExpr
{
    public abstract JinjaValue Eval(JinjaScope scope);
}

internal sealed class LiteralExpr(JinjaValue value) : JinjaExpr
{
    public override JinjaValue Eval(JinjaScope scope) => value;
}

internal sealed class NameExpr(string name) : JinjaExpr
{
    public string Name { get; } = name;

    public override JinjaValue Eval(JinjaScope scope) => scope.Get(Name);
}

internal sealed class ListExpr(IReadOnlyList<JinjaExpr> items) : JinjaExpr
{
    public override JinjaValue Eval(JinjaScope scope)
    {
        List<JinjaValue> values = new(items.Count);
        foreach (JinjaExpr e in items)
        {
            values.Add(e.Eval(scope));
        }

        return JinjaValue.Of(values);
    }
}

internal sealed class AttrExpr(JinjaExpr target, string name) : JinjaExpr
{
    public JinjaExpr Target { get; } = target;

    public string Name { get; } = name;

    public override JinjaValue Eval(JinjaScope scope)
    {
        JinjaValue t = Target.Eval(scope);
        return t.Kind is JinjaKind.Undefined ? JinjaValue.Undefined : t.TryField(Name, out JinjaValue v) ? v : JinjaValue.Undefined;
    }
}

internal sealed class ItemExpr(JinjaExpr target, JinjaExpr key) : JinjaExpr
{
    public override JinjaValue Eval(JinjaScope scope)
    {
        JinjaValue t = target.Eval(scope);
        JinjaValue k = key.Eval(scope);
        if (t.Kind == JinjaKind.Undefined)
        {
            return JinjaValue.Undefined;
        }

        switch (t.Kind)
        {
            case JinjaKind.List:
                {
                    long idx = Index(k, t.Items.Count);
                    return t.Items[(int)idx];
                }

            case JinjaKind.Str:
                {
                    long idx = Index(k, t.AsString.Length);
                    return JinjaValue.Of(t.AsString[(int)idx].ToString());
                }

            case JinjaKind.Dict:
            case JinjaKind.Namespace:
                return t.TryField(k.Display(), out JinjaValue v) ? v : JinjaValue.Undefined;
            default:
                throw new JinjaEvaluationException($"不可下标: {t.Kind}[{k.Display()}]");
        }
    }

    private static long Index(JinjaValue key, int count)
    {
        if (key.Kind != JinjaKind.Int)
        {
            throw new JinjaEvaluationException($"下标须为整数, 得到 {key.Kind}");
        }

        long i = key.AsInt;
        long norm = i < 0 ? count + i : i;
        if (norm < 0 || norm >= count)
        {
            throw new JinjaEvaluationException($"下标越界: {i} (长度 {count})");
        }

        return norm;
    }
}

internal sealed class UnaryExpr(string op, JinjaExpr operand) : JinjaExpr
{
    public override JinjaValue Eval(JinjaScope scope)
    {
        JinjaValue v = operand.Eval(scope);
        return op switch
        {
            "not" => JinjaValue.Of(!v.Truthy()),
            "-" => v.Kind switch
            {
                JinjaKind.Int => JinjaValue.Of(-v.AsInt),
                JinjaKind.Num => JinjaValue.Of(-v.AsNum),
                _ => throw new JinjaEvaluationException($"一元 - 不支持 {v.Kind}"),
            },
            "+" => v,
            _ => throw new JinjaUnsupportedException($"一元运算符 {op}"),
        };
    }
}

internal sealed class BinaryExpr(string op, JinjaExpr left, JinjaExpr right) : JinjaExpr
{
    public override JinjaValue Eval(JinjaScope scope)
    {
        // and/or 返回操作数本身 (Python 语义), 并短路
        if (op == "and")
        {
            JinjaValue l = left.Eval(scope);
            return l.Truthy() ? right.Eval(scope) : l;
        }

        if (op == "or")
        {
            JinjaValue l = left.Eval(scope);
            return l.Truthy() ? l : right.Eval(scope);
        }

        JinjaValue a = left.Eval(scope);
        JinjaValue b = right.Eval(scope);
        switch (op)
        {
            case "==":
                return JinjaValue.Of(a.ValueEquals(b));
            case "!=":
                return JinjaValue.Of(!a.ValueEquals(b));
            case "<":
                return JinjaValue.Of(a.CompareTo(b) < 0);
            case "<=":
                return JinjaValue.Of(a.CompareTo(b) <= 0);
            case ">":
                return JinjaValue.Of(a.CompareTo(b) > 0);
            case ">=":
                return JinjaValue.Of(a.CompareTo(b) >= 0);
            case "in":
                return JinjaValue.Of(Contains(b, a));
            case "not in":
                return JinjaValue.Of(!Contains(b, a));
            case "+":
                if (a.Kind == JinjaKind.Str && b.Kind == JinjaKind.Str)
                {
                    return JinjaValue.Of(a.AsString + b.AsString);
                }

                if (a.Kind == JinjaKind.List && b.Kind == JinjaKind.List)
                {
                    return JinjaValue.Of((IReadOnlyList<JinjaValue>)[.. a.Items, .. b.Items]);
                }

                if (a.Kind == JinjaKind.Int && b.Kind == JinjaKind.Int)
                {
                    return JinjaValue.Of(a.AsInt + b.AsInt);
                }

                if (IsNum(a) && IsNum(b))
                {
                    return JinjaValue.Of(a.AsNum + b.AsNum);
                }

                throw new JinjaEvaluationException($"+ 不支持 {a.Kind} 与 {b.Kind} (字符串拼接要求两侧皆字符串)");
            case "-":
                return JinjaValue.Of(a.AsInt - b.AsInt);
            case "*":
                if (a.Kind == JinjaKind.Int && b.Kind == JinjaKind.Str)
                {
                    return JinjaValue.Of(string.Concat(Enumerable.Repeat(b.AsString, (int)a.AsInt)));
                }

                return JinjaValue.Of(a.AsInt * b.AsInt);
            case "//":
                return JinjaValue.Of(a.AsInt / b.AsInt);
            case "/":
                return JinjaValue.Of((double)a.AsInt / b.AsInt);
            case "%":
                return JinjaValue.Of(a.AsInt % b.AsInt);
            case "~":
                return JinjaValue.Of(a.Display() + b.Display());
            default:
                throw new JinjaUnsupportedException($"二元运算符 {op}");
        }
    }

    private static bool IsNum(JinjaValue v) => v.Kind is JinjaKind.Int or JinjaKind.Num;

    private static bool Contains(JinjaValue container, JinjaValue needle)
    {
        switch (container.Kind)
        {
            case JinjaKind.Str:
                return needle.Kind == JinjaKind.Str && container.AsString.Contains(needle.AsString, StringComparison.Ordinal);
            case JinjaKind.List:
                return container.Items.Any(x => x.ValueEquals(needle));
            case JinjaKind.Dict:
            case JinjaKind.Namespace:
                return container.TryField(needle.Display(), out _);
            case JinjaKind.Undefined:
                throw new JinjaEvaluationException("对未定义值做 in 判定 (jinja 亦抛错)");
            default:
                throw new JinjaEvaluationException($"in 不支持容器 {container.Kind}");
        }
    }
}

internal sealed class IsTestExpr(JinjaExpr target, string test, bool negated) : JinjaExpr
{
    public override JinjaValue Eval(JinjaScope scope)
    {
        JinjaValue v = target.Eval(scope);
        bool result = test switch
        {
            "defined" => v.IsDefined,
            "undefined" => v.IsUndefined,
            "none" => v.IsNull,
            "true" => v.Kind == JinjaKind.Bool && v.AsBool,
            "false" => v.Kind == JinjaKind.Bool && !v.AsBool,
            "string" => v.Kind == JinjaKind.Str,
            "number" => v.Kind is JinjaKind.Int or JinjaKind.Num,
            "mapping" => v.Kind is JinjaKind.Dict or JinjaKind.Namespace,
            "iterable" => v.Kind is JinjaKind.List or JinjaKind.Str or JinjaKind.Dict or JinjaKind.Namespace,
            _ => throw new JinjaUnsupportedException($"is 测试 '{test}' 未实现"),
        };
        return JinjaValue.Of(negated ? !result : result);
    }
}

internal sealed class FuncCallExpr(string name, IReadOnlyList<JinjaExpr> args, IReadOnlyList<KeyValuePair<string, JinjaExpr>> kwargs) : JinjaExpr
{
    public override JinjaValue Eval(JinjaScope scope)
    {
        switch (name)
        {
            case "namespace":
                {
                    Dictionary<string, JinjaValue> fields = new(StringComparer.Ordinal);
                    foreach (KeyValuePair<string, JinjaExpr> kv in kwargs)
                    {
                        fields[kv.Key] = kv.Value.Eval(scope);
                    }

                    return JinjaValue.Namespace(fields);
                }

            case "range":
                {
                    long n = args.Count > 0 ? args[0].Eval(scope).AsInt : 0;
                    List<JinjaValue> items = [];
                    for (long i = 0; i < n; i++)
                    {
                        items.Add(JinjaValue.Of(i));
                    }

                    return JinjaValue.Of(items);
                }

            case "raise_exception":
                throw new JinjaEvaluationException(args.Count > 0 ? args[0].Eval(scope).Display() : "模板 raise_exception()");

            case "dict":
                {
                    Dictionary<string, JinjaValue> fields = new(StringComparer.Ordinal);
                    foreach (KeyValuePair<string, JinjaExpr> kv in kwargs)
                    {
                        fields[kv.Key] = kv.Value.Eval(scope);
                    }

                    return JinjaValue.Dict(fields);
                }

            default:
                throw new JinjaUnsupportedException($"函数 {name}() 未实现");
        }
    }
}

internal sealed class MethodCallExpr(JinjaExpr target, string method, IReadOnlyList<JinjaExpr> args) : JinjaExpr
{
    public override JinjaValue Eval(JinjaScope scope)
    {
        JinjaValue t = target.Eval(scope);
        List<JinjaValue> a = [];
        foreach (JinjaExpr e in args)
        {
            a.Add(e.Eval(scope));
        }

        string Arg(int i) => i < a.Count ? a[i].Display() : throw new JinjaEvaluationException($"{method}() 缺第 {i + 1} 个参数");
        switch (t.Kind)
        {
            case JinjaKind.Str:
                {
                    string s = t.AsString;
                    return method switch
                    {
                        "split" => JinjaValue.Of((IReadOnlyList<JinjaValue>)[.. s.Split(Arg(0), StringSplitOptions.None).Select(JinjaValue.Of)]),
                        "strip" => JinjaValue.Of(s.Trim()),
                        "lstrip" => JinjaValue.Of(s.TrimStart()),
                        "rstrip" => JinjaValue.Of(s.TrimEnd()),
                        "lower" => JinjaValue.Of(s.ToLowerInvariant()),
                        "upper" => JinjaValue.Of(s.ToUpperInvariant()),
                        "replace" => JinjaValue.Of(s.Replace(Arg(0), Arg(1), StringComparison.Ordinal)),
                        "startswith" => JinjaValue.Of(s.StartsWith(Arg(0), StringComparison.Ordinal)),
                        "endswith" => JinjaValue.Of(s.EndsWith(Arg(0), StringComparison.Ordinal)),
                        "join" => JinjaValue.Of(string.Join(s, a.Count > 0 && a[0].Kind == JinjaKind.List ? a[0].Items.Select(x => x.Display()) : a.Select(x => x.Display()))),
                        _ => throw new JinjaUnsupportedException($"字符串方法 .{method}() 未实现"),
                    };
                }

            case JinjaKind.List:
                return method switch
                {
                    "count" => JinjaValue.Of(t.Items.Count(x => a.Count > 0 && x.ValueEquals(a[0]))),
                    "index" => JinjaValue.Of(t.Items.ToList().FindIndex(x => a.Count > 0 && x.ValueEquals(a[0]))),
                    _ => throw new JinjaUnsupportedException($"列表方法 .{method}() 未实现"),
                };

            case JinjaKind.Dict:
            case JinjaKind.Namespace:
                return method switch
                {
                    "get" => t.TryField(Arg(0), out JinjaValue v) ? v : a.Count > 1 ? a[1] : JinjaValue.Null,
                    "keys" => JinjaValue.Of((IReadOnlyList<JinjaValue>)[.. (t.Fields ?? new Dictionary<string, JinjaValue>()).Keys.Select(JinjaValue.Of)]),
                    "values" => JinjaValue.Of((IReadOnlyList<JinjaValue>)[.. (t.Fields ?? new Dictionary<string, JinjaValue>()).Values]),
                    _ => throw new JinjaUnsupportedException($"字典方法 .{method}() 未实现"),
                };

            default:
                throw new JinjaEvaluationException($"对 {t.Kind} 调用 .{method}()");
        }
    }
}

internal sealed class FilterExpr(JinjaExpr target, string name) : JinjaExpr
{
    public override JinjaValue Eval(JinjaScope scope)
    {
        JinjaValue v = target.Eval(scope);
        return name switch
        {
            "tojson" => JinjaValue.Of(v.ToJson()),
            "trim" => JinjaValue.Of(v.Display().Trim()),
            "upper" => JinjaValue.Of(v.Display().ToUpperInvariant()),
            "lower" => JinjaValue.Of(v.Display().ToLowerInvariant()),
            "string" => JinjaValue.Of(v.Display()),
            "length" or "count" => JinjaValue.Of(v.Kind switch
            {
                JinjaKind.Str => v.AsString.Length,
                JinjaKind.List => v.Items.Count,
                JinjaKind.Dict or JinjaKind.Namespace => (v.Fields ?? new Dictionary<string, JinjaValue>()).Count,
                _ => throw new JinjaEvaluationException($"length 不支持 {v.Kind}"),
            }),
            _ => throw new JinjaUnsupportedException($"过滤器 |{name} 未实现"),
        };
    }
}

internal sealed class UnsupportedExpr(string reason) : JinjaExpr
{
    public override JinjaValue Eval(JinjaScope scope) => throw new JinjaUnsupportedException(reason);
}

/// <summary>
/// 递归下降表达式解析器 (优先级: or &lt; and &lt; not &lt; 比较/is/in &lt; +/-/~ &lt; * // % &lt; 一元 &lt; 后缀)。
/// 无法解析的片段不抛异常, 而是解析成「求值到才抛」的 <see cref="UnsupportedExpr"/> ——
/// 保证未走到的分支不会让整份模板不可用 (例如 tool 分支)。
/// </summary>
internal sealed class JinjaExprParser
{
    private readonly List<JinjaToken> _tokens;
    private int _i;

    private JinjaExprParser(List<JinjaToken> tokens) => _tokens = tokens;

    public static JinjaExpr Parse(string text)
    {
        List<JinjaToken> tokens = JinjaExprLexer.Tokenize(text);
        JinjaExprParser p = new(tokens);
        JinjaExpr e = p.ParseOr();
        if (p.Peek().Kind != JinjaTokenKind.End)
        {
            return new UnsupportedExpr($"表达式无法完整解析 (剩 '{p.Peek().Text}'; 原文: {text.Trim()})");
        }

        return e;
    }

    private JinjaToken Peek() => _tokens[_i];

    private JinjaToken Next() => _tokens[_i++];

    private bool Take(string text)
    {
        if (string.Equals(Peek().Text, text, StringComparison.Ordinal))
        {
            _i++;
            return true;
        }

        return false;
    }

    private void Expect(string text)
    {
        if (!Take(text))
        {
            throw new JinjaEvaluationException($"期望 '{text}', 实际 '{Peek().Text}'");
        }
    }

    private JinjaExpr ParseOr()
    {
        JinjaExpr left = ParseAnd();
        while (Peek().Kind == JinjaTokenKind.Keyword && Peek().Text is "or")
        {
            Next();
            left = new BinaryExpr("or", left, ParseAnd());
        }

        return left;
    }

    private JinjaExpr ParseAnd()
    {
        JinjaExpr left = ParseNot();
        while (Peek().Kind == JinjaTokenKind.Keyword && Peek().Text is "and")
        {
            Next();
            left = new BinaryExpr("and", left, ParseNot());
        }

        return left;
    }

    private JinjaExpr ParseNot()
    {
        if (Peek().Kind == JinjaTokenKind.Keyword && Peek().Text is "not")
        {
            Next();
            return new UnaryExpr("not", ParseNot());
        }

        return ParseComparison();
    }

    private JinjaExpr ParseComparison()
    {
        JinjaExpr left = ParseAdd();
        while (true)
        {
            JinjaToken t = Peek();
            if (t.Kind == JinjaTokenKind.Punct && t.Text is "==" or "!=" or "<" or "<=" or ">" or ">=")
            {
                Next();
                left = new BinaryExpr(t.Text, left, ParseAdd());
                continue;
            }

            if (t.Kind == JinjaTokenKind.Keyword && t.Text is "in")
            {
                Next();
                left = new BinaryExpr("in", left, ParseAdd());
                continue;
            }

            if (t.Kind == JinjaTokenKind.Keyword && t.Text is "not" && _tokens[_i + 1].Text is "in")
            {
                Next();
                Next();
                left = new BinaryExpr("not in", left, ParseAdd());
                continue;
            }

            if (t.Kind == JinjaTokenKind.Keyword && t.Text is "is")
            {
                Next();
                bool negated = Take("not");
                JinjaToken name = Peek();
                if (name.Kind is not (JinjaTokenKind.Name or JinjaTokenKind.Keyword))
                {
                    throw new JinjaEvaluationException($"is 后应为测试名, 实际 '{name.Text}'");
                }

                Next();
                left = new IsTestExpr(left, name.Text, negated);
                continue;
            }

            return left;
        }
    }

    private JinjaExpr ParseAdd()
    {
        JinjaExpr left = ParseMul();
        while (Peek().Kind == JinjaTokenKind.Punct && Peek().Text is "+" or "-" or "~")
        {
            string op = Next().Text;
            left = new BinaryExpr(op, left, ParseMul());
        }

        return left;
    }

    private JinjaExpr ParseMul()
    {
        JinjaExpr left = ParseUnary();
        while (Peek().Kind == JinjaTokenKind.Punct && Peek().Text is "*" or "/" or "//" or "%")
        {
            string op = Next().Text;
            left = new BinaryExpr(op, left, ParseUnary());
        }

        return left;
    }

    private JinjaExpr ParseUnary()
    {
        if (Peek().Kind == JinjaTokenKind.Punct && Peek().Text is "-" or "+")
        {
            string op = Next().Text;
            return new UnaryExpr(op, ParseUnary());
        }

        return ParsePostfix();
    }

    private JinjaExpr ParsePostfix()
    {
        JinjaExpr e = ParsePrimary();
        while (true)
        {
            if (Take("."))
            {
                string name = NextName();
                e = Take("(") ? new MethodCallExpr(e, name, ParseArgs().Args) : new AttrExpr(e, name);
                continue;
            }

            if (Take("["))
            {
                JinjaExpr key = ParseOr();
                Expect("]");
                e = new ItemExpr(e, key);
                continue;
            }

            if (Peek().Kind == JinjaTokenKind.Punct && Peek().Text is "(")
            {
                Next();
                (IReadOnlyList<JinjaExpr> args, IReadOnlyList<KeyValuePair<string, JinjaExpr>> kwargs) = ParseArgs();
                e = e is NameExpr n
                    ? new FuncCallExpr(n.Name, args, kwargs)
                    : new UnsupportedExpr("对非函数名调用 ()");
                continue;
            }

            if (Take("|"))
            {
                string name = NextName();
                e = new FilterExpr(e, name);
                continue;
            }

            return e;
        }
    }

    private string NextName()
    {
        JinjaToken t = Peek();
        if (t.Kind is not (JinjaTokenKind.Name or JinjaTokenKind.Keyword))
        {
            throw new JinjaEvaluationException($"期望名字, 实际 '{t.Text}'");
        }

        Next();
        return t.Text;
    }

    private (IReadOnlyList<JinjaExpr> Args, IReadOnlyList<KeyValuePair<string, JinjaExpr>> Kwargs) ParseArgs()
    {
        List<JinjaExpr> args = [];
        List<KeyValuePair<string, JinjaExpr>> kwargs = [];
        if (Take(")"))
        {
            return (args, kwargs);
        }

        while (true)
        {
            if (Peek().Kind == JinjaTokenKind.Name && _tokens[_i + 1].Text is "=")
            {
                string key = Next().Text;
                Next();
                kwargs.Add(new KeyValuePair<string, JinjaExpr>(key, ParseOr()));
            }
            else
            {
                args.Add(ParseOr());
            }

            if (Take(")"))
            {
                return (args, kwargs);
            }

            Expect(",");
        }
    }

    private JinjaExpr ParsePrimary()
    {
        JinjaToken t = Peek();
        switch (t.Kind)
        {
            case JinjaTokenKind.Int:
                Next();
                return new LiteralExpr(JinjaValue.Of(t.IntValue));
            case JinjaTokenKind.Num:
                Next();
                return new LiteralExpr(JinjaValue.Of(t.NumValue));
            case JinjaTokenKind.Str:
                Next();
                return new LiteralExpr(JinjaValue.Of(t.Text));
            case JinjaTokenKind.Name:
                Next();
                return new NameExpr(t.Text);
            case JinjaTokenKind.Keyword:
                Next();
                return t.Text switch
                {
                    "true" or "True" => new LiteralExpr(JinjaValue.True),
                    "false" or "False" => new LiteralExpr(JinjaValue.False),
                    "none" or "None" => new LiteralExpr(JinjaValue.Null),
                    _ => new UnsupportedExpr($"关键字 '{t.Text}' 不能作为表达式起始"),
                };
            case JinjaTokenKind.Punct when t.Text is "(":
                Next();
                {
                    JinjaExpr inner = ParseOr();
                    Expect(")");
                    return inner;
                }

            case JinjaTokenKind.Punct when t.Text is "[":
                Next();
                {
                    List<JinjaExpr> items = [];
                    if (!Take("]"))
                    {
                        while (true)
                        {
                            items.Add(ParseOr());
                            if (Take("]"))
                            {
                                break;
                            }

                            Expect(",");
                        }
                    }

                    return new ListExpr(items);
                }

            default:
                Next();
                return new UnsupportedExpr($"表达式片段 '{t.Text}' 未实现");
        }
    }
}
