using System.Globalization;
using System.Text;

namespace agent.rover.token;

/// <summary>Jinja 运行时值类别 (R406 Jinja 子集解释器: 与 Python/jinja2 对齐的最小闭集)。</summary>
public enum JinjaKind
{
    /// <summary>未定义 —— jinja 默认 Undefined: 假值、渲染为空串、取属性/下标仍为 Undefined。</summary>
    Undefined,
    Null,
    Bool,
    Int,
    Num,
    Str,
    List,
    Dict,
    Namespace,
}

/// <summary>
/// Jinja 值。本体不可变; 仅 Dict/Namespace 的字段字典可变 —— 对应 jinja 的 <c>namespace()</c> 语义
/// (跨循环迭代写回, 是 tool_calls 分支状态机的依赖)。
/// 零反射 / AOT 安全: JSON 手写序列化, 不依赖反射或源生成器。
/// </summary>
public sealed class JinjaValue
{
    private readonly bool _bool;
    private readonly long _int;
    private readonly double _num;
    private readonly string? _str;
    private readonly IReadOnlyList<JinjaValue>? _items;
    private readonly IDictionary<string, JinjaValue>? _fields;

    public JinjaKind Kind { get; }

    private JinjaValue(
        JinjaKind kind,
        bool b = false,
        long i = 0,
        double n = 0,
        string? s = null,
        IReadOnlyList<JinjaValue>? items = null,
        IDictionary<string, JinjaValue>? fields = null)
    {
        Kind = kind;
        _bool = b;
        _int = i;
        _num = n;
        _str = s;
        _items = items;
        _fields = fields;
    }

    public static JinjaValue Undefined { get; } = new(JinjaKind.Undefined);

    public static JinjaValue Null { get; } = new(JinjaKind.Null);

    public static JinjaValue True { get; } = new(JinjaKind.Bool, b: true);

    public static JinjaValue False { get; } = new(JinjaKind.Bool, b: false);

    public static JinjaValue Of(bool b) => b ? True : False;

    public static JinjaValue Of(long i) => new(JinjaKind.Int, i: i);

    public static JinjaValue Of(double d) => new(JinjaKind.Num, n: d);

    public static JinjaValue Of(string s) => new(JinjaKind.Str, s: s);

    public static JinjaValue Of(IReadOnlyList<JinjaValue> items) => new(JinjaKind.List, items: items);

    public static JinjaValue Dict() => new(JinjaKind.Dict, fields: new Dictionary<string, JinjaValue>(StringComparer.Ordinal));

    public static JinjaValue Dict(IDictionary<string, JinjaValue> fields) => new(JinjaKind.Dict, fields: fields);

    public static JinjaValue Namespace(IDictionary<string, JinjaValue> fields) => new(JinjaKind.Namespace, fields: fields);

    public bool IsUndefined => Kind == JinjaKind.Undefined;

    public bool IsNull => Kind == JinjaKind.Null;

    /// <summary>jinja 的 <c>is defined</c>: 只判 Undefined (Null 是 defined 的)。</summary>
    public bool IsDefined => Kind != JinjaKind.Undefined;

    public bool AsBool => _bool;

    public long AsInt => _int;

    public double AsNum => Kind == JinjaKind.Int ? _int : _num;

    public string AsString => _str ?? string.Empty;

    public IReadOnlyList<JinjaValue> Items => _items ?? [];

    /// <summary>Dict/Namespace 的字段集合 (只读视图; 元素可写)。</summary>
    public IReadOnlyDictionary<string, JinjaValue>? Fields => _fields as IReadOnlyDictionary<string, JinjaValue>;

    public bool TryField(string name, out JinjaValue value)
    {
        if (_fields is not null && _fields.TryGetValue(name, out JinjaValue? v))
        {
            value = v;
            return true;
        }

        value = Undefined;
        return false;
    }

    /// <summary>命名空间字段写入 (仅 Namespace/Dict; 其余抛 <see cref="JinjaEvaluationException"/>)。</summary>
    public void SetField(string name, JinjaValue value)
    {
        if (_fields is null)
        {
            throw new JinjaEvaluationException($"对 {Kind} 取属性赋值 (仅 namespace/dict 可写): .{name}");
        }

        _fields[name] = value;
    }

    /// <summary>Python 真值规则: Undefined/Null/0/""/空表/空字典 为假。</summary>
    public bool Truthy() => Kind switch
    {
        JinjaKind.Undefined or JinjaKind.Null => false,
        JinjaKind.Bool => _bool,
        JinjaKind.Int => _int != 0,
        JinjaKind.Num => _num != 0,
        JinjaKind.Str => _str!.Length > 0,
        JinjaKind.List => _items!.Count > 0,
        JinjaKind.Dict or JinjaKind.Namespace => _fields!.Count > 0,
        _ => false,
    };

    /// <summary>jinja 的 str() 渲染规则 (Undefined 渲染为空串; None 渲染为 "None")。</summary>
    public string Display()
    {
        switch (Kind)
        {
            case JinjaKind.Undefined:
                return string.Empty;
            case JinjaKind.Null:
                return "None";
            case JinjaKind.Bool:
                return _bool ? "True" : "False";
            case JinjaKind.Int:
                return _int.ToString(CultureInfo.InvariantCulture);
            case JinjaKind.Num:
                return _num.ToString("R", CultureInfo.InvariantCulture);
            case JinjaKind.Str:
                return _str!;
            case JinjaKind.List:
                return "[" + string.Join(", ", _items!.Select(x => x.Repr())) + "]";
            default:
                {
                    StringBuilder sb = new("{");
                    bool first = true;
                    foreach (KeyValuePair<string, JinjaValue> kv in _fields!)
                    {
                        if (!first)
                        {
                            sb.Append(", ");
                        }

                        sb.Append('\'').Append(kv.Key).Append("': ").Append(kv.Value.Repr());
                        first = false;
                    }

                    return sb.Append('}').ToString();
                }
        }
    }

    /// <summary>列表/字典内部元素的 repr (字符串带引号, 与 Python repr 一致)。</summary>
    private string Repr() => Kind == JinjaKind.Str ? "'" + _str + "'" : Display();

    public bool ValueEquals(JinjaValue other)
    {
        if (Kind != other.Kind)
        {
            // Python: True == 1; 其余跨类比较为 False
            if (Kind == JinjaKind.Bool && other.Kind == JinjaKind.Int)
            {
                return (_bool ? 1 : 0) == other._int;
            }

            if (Kind == JinjaKind.Int && other.Kind == JinjaKind.Bool)
            {
                return _int == (other._bool ? 1 : 0);
            }

            if ((Kind == JinjaKind.Int && other.Kind == JinjaKind.Num) || (Kind == JinjaKind.Num && other.Kind == JinjaKind.Int))
            {
                return AsNum == other.AsNum;
            }

            return false;
        }

        return Kind switch
        {
            JinjaKind.Undefined or JinjaKind.Null => true,
            JinjaKind.Bool => _bool == other._bool,
            JinjaKind.Int => _int == other._int,
            JinjaKind.Num => _num.Equals(other._num),
            JinjaKind.Str => string.Equals(_str, other._str, StringComparison.Ordinal),
            JinjaKind.List => _items!.Count == other._items!.Count
                && _items.Zip(other._items).All(p => p.First.ValueEquals(p.Second)),
            _ => _fields!.Count == other._fields!.Count
                && _fields.All(kv => other._fields.TryGetValue(kv.Key, out JinjaValue? v) && v.ValueEquals(kv.Value)),
        };
    }

    /// <summary>数值/字符串序比较 (&lt; &lt;= &gt; &gt;=); 不可比类型抛异常 (不静默返回 false)。</summary>
    public int CompareTo(JinjaValue other)
    {
        if (Kind == JinjaKind.Str && other.Kind == JinjaKind.Str)
        {
            return string.CompareOrdinal(_str, other._str);
        }

        if (IsNumeric(Kind) && IsNumeric(other.Kind))
        {
            return AsNum.CompareTo(other.AsNum);
        }

        throw new JinjaEvaluationException($"不可比较: {Kind} 与 {other.Kind}");
    }

    private static bool IsNumeric(JinjaKind k) => k is JinjaKind.Int or JinjaKind.Num or JinjaKind.Bool;

    /// <summary>
    /// 手写 JSON 序列化 (jinja <c>| tojson</c>)。分隔符按 Python json.dumps 默认 (", " / ": ")。
    /// 注: 仅 tool 分支使用, **未被夹具覆盖** (tool 角色为 R400 排除项), 属未验证路径。
    /// </summary>
    public string ToJson()
    {
        StringBuilder sb = new();
        WriteJson(sb);
        return sb.ToString();
    }

    private void WriteJson(StringBuilder sb)
    {
        switch (Kind)
        {
            case JinjaKind.Undefined:
            case JinjaKind.Null:
                sb.Append("null");
                break;
            case JinjaKind.Bool:
                sb.Append(_bool ? "true" : "false");
                break;
            case JinjaKind.Int:
                sb.Append(_int.ToString(CultureInfo.InvariantCulture));
                break;
            case JinjaKind.Num:
                sb.Append(_num.ToString("R", CultureInfo.InvariantCulture));
                break;
            case JinjaKind.Str:
                WriteJsonString(sb, _str!);
                break;
            case JinjaKind.List:
                sb.Append('[');
                for (int i = 0; i < _items!.Count; i++)
                {
                    if (i > 0)
                    {
                        sb.Append(", ");
                    }

                    _items[i].WriteJson(sb);
                }

                sb.Append(']');
                break;
            default:
                sb.Append('{');
                {
                    bool first = true;
                    foreach (KeyValuePair<string, JinjaValue> kv in _fields!)
                    {
                        if (!first)
                        {
                            sb.Append(", ");
                        }

                        WriteJsonString(sb, kv.Key);
                        sb.Append(": ");
                        kv.Value.WriteJson(sb);
                        first = false;
                    }
                }

                sb.Append('}');
                break;
        }
    }

    private static void WriteJsonString(StringBuilder sb, string s)
    {
        sb.Append('"');
        foreach (char c in s)
        {
            switch (c)
            {
                case '"':
                    sb.Append("\\\"");
                    break;
                case '\\':
                    sb.Append("\\\\");
                    break;
                case '\n':
                    sb.Append("\\n");
                    break;
                case '\r':
                    sb.Append("\\r");
                    break;
                case '\t':
                    sb.Append("\\t");
                    break;
                default:
                    if (c < 0x20)
                    {
                        sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                    }
                    else
                    {
                        sb.Append(c);
                    }

                    break;
            }
        }

        sb.Append('"');
    }
}
