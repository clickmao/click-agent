using System.Globalization;
using System.Text;

namespace agent.r1;

/// <summary>
/// R1 管道 · 手写 JSON 输出（铁律：AOT 下 STJ 反射序列化不可用 ⇒ 全部零反射手写，
/// 转义规则与 RFC 8259 一致；数值一律 InvariantCulture，禁本地化小数点）。
/// </summary>
public static class R1Json
{
    public static string Quote(string? s)
    {
        var sb = new StringBuilder("\"");
        foreach (var ch in s ?? string.Empty)
        {
            switch (ch)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                case '\b': sb.Append("\\b"); break;
                case '\f': sb.Append("\\f"); break;
                default:
                    if (ch < 0x20)
                    {
                        sb.Append("\\u").Append(((int)ch).ToString("x4", CultureInfo.InvariantCulture));
                    }
                    else
                    {
                        sb.Append(ch);
                    }
                    break;
            }
        }
        return sb.Append('"').ToString();
    }

    public static string Num(double d) => d.ToString("0.####", CultureInfo.InvariantCulture);

    public static string Num(int i) => i.ToString(CultureInfo.InvariantCulture);

    public static string Num(long i) => i.ToString(CultureInfo.InvariantCulture);

    /// <summary>可空整数：null ⇒ JSON null（禁把“未上报”写成 0）。</summary>
    public static string NumOrNull(int? i) => i.HasValue ? Num(i.Value) : "null";
}
