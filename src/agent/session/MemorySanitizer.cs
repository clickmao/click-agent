using System.Text.Json.Serialization;

namespace agent.session;


/// <summary>记忆净化: 写入前剥离疑似凭据 (对齐偏好库铁律: 记忆不存凭据)</summary>
public static class MemorySanitizer
{
    public static string StripSecrets(string text)
    {
        if (string.IsNullOrEmpty(text))
            return text;
        // token/key/password 形态: 赋值段打码 (保留键名, 值换 [REDACTED])
        var sb = new System.Text.StringBuilder(text.Length);
        var lower = text.ToLowerInvariant();
        int i = 0;
        while (i < text.Length)
        {
            var hit = FindSecretKeyword(lower, i);
            if (hit < 0)
            {
                sb.Append(text[i..]);
                break;
            }
            sb.Append(text[i..hit]);
            i = hit;
            // 关键字后找分隔符 (=/:) 与值
            var sep = text.IndexOfAny(new[] { '=', ':', '：' }, hit);
            if (sep < 0 || sep - hit > 24)
            {
                // 不是赋值形态, 只是普通词, 原样跳过关键字
                sb.Append(text[hit..Math.Min(text.Length, hit + 12)]);
                i = Math.Min(text.Length, hit + 12);
                continue;
            }
            sb.Append(text[hit..(sep + 1)]);
            // 值段: 非空白即打码
            int v = sep + 1;
            while (v < text.Length && char.IsWhiteSpace(text[v]))
            {
                sb.Append(text[v]);
                v++;
            }
            var vend = v;
            while (vend < text.Length && !char.IsWhiteSpace(text[vend]))
                vend++;
            sb.Append(vend > v ? "[REDACTED]" : string.Empty);
            i = Math.Max(vend, v);
        }
        return sb.ToString();
    }

    private static int FindSecretKeyword(string lower, int from)
    {
        string[] keys = { "api_key", "apikey", "token", "password", "passwd", "secret", "ghp_" };
        var best = -1;
        foreach (var k in keys)
        {
            var idx = lower.IndexOf(k, from, StringComparison.Ordinal);
            if (idx >= 0 && (best < 0 || idx < best))
                best = idx;
        }
        return best;
    }
}
