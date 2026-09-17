namespace agent.r1;

/// <summary>R1 管道 · 文本裁剪（读数一律带长度，禁静默截断）。</summary>
public static class R1Text
{
    public static string Tail(string? s, int n)
    {
        var t = s ?? string.Empty;
        if (t.Length <= n)
        {
            return t;
        }
        return "…(" + (t.Length - n).ToString(System.Globalization.CultureInfo.InvariantCulture) + " ch dropped)…" + t[^n..];
    }
}
