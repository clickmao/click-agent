// R480: 独立文本召回模块 —— 测量器具 (真实语料质量臂 + 同比例压缩规模臂 + 增量保鲜臂)。
// 纪律: 所有数字来自本进程真实执行; 合成语料一律在 JSON 里标 "synthetic": true, 不与真实语料混算。
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using agent.recall;

namespace agent.recall.bench;


/// <summary>手写 JSON (零反射 / AOT 安全): 只做本器具所需的最小写法。</summary>
internal sealed class JsonOut
{
    private readonly StringBuilder _sb = new();
    private readonly Stack<bool> _first = new();

    public void BeginObject()
    {
        _sb.Append('{');
        _first.Push(true);
    }

    public void BeginObject(string name)
    {
        PropPrefix(name);
        _sb.Append('{');
        _first.Push(true);
    }

    public void EndObject()
    {
        _sb.Append('}');
        _first.Pop();
    }

    public void BeginArray(string name)
    {
        PropPrefix(name);
        _sb.Append('[');
        _first.Push(true);
    }

    public void EndArray()
    {
        _sb.Append(']');
        _first.Pop();
    }

    public void Prop(string name, string value)
    {
        PropPrefix(name);
        _sb.Append('"').Append(Escape(value)).Append('"');
    }

    public void Prop(string name, long value)
    {
        PropPrefix(name);
        _sb.Append(value);
    }

    public void Prop(string name, double value)
    {
        PropPrefix(name);
        _sb.Append(value.ToString("R", System.Globalization.CultureInfo.InvariantCulture));
    }

    public void Prop(string name, bool value)
    {
        PropPrefix(name);
        _sb.Append(value ? "true" : "false");
    }

    public void PropRaw(string name, string rawJson)
    {
        PropPrefix(name);
        _sb.Append(rawJson);
    }

    public void Raw(string rawJson)
    {
        if (_first.Count > 0 && _first.Peek())
        {
            _first.Pop();
            _first.Push(false);
        }
        else
        {
            _sb.Append(',');
        }
        _sb.Append(rawJson);
    }

    private void PropPrefix(string name)
    {
        if (_first.Count > 0 && _first.Peek())
        {
            _first.Pop();
            _first.Push(false);
        }
        else
        {
            _sb.Append(',');
        }
        _sb.Append('"').Append(Escape(name)).Append("\":");
    }

    private static string Escape(string s)
    {
        var sb = new StringBuilder(s.Length + 8);
        foreach (char c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (c < 0x20)
                    {
                        sb.Append("\\u").Append(((int)c).ToString("x4"));
                    }
                    else
                    {
                        sb.Append(c);
                    }
                    break;
            }
        }
        return sb.ToString();
    }

    public override string ToString() => _sb.ToString();
}
