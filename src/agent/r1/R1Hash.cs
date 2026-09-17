using System.Security.Cryptography;
using System.Text;

namespace agent.r1;

/// <summary>R1 管道 · 摘要工具（AOT 无反射，只用 SHA256.HashData 静态入口）。</summary>
public static class R1Hash
{
    public static string OfBytes(byte[] data)
    {
        var h = SHA256.HashData(data);
        var sb = new StringBuilder(64);
        foreach (var b in h)
        {
            sb.Append(b.ToString("x2"));
        }
        return sb.ToString();
    }

    public static string OfText(string text) => OfBytes(Encoding.UTF8.GetBytes(text ?? string.Empty));
}
