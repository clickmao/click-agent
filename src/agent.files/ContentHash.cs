using System.Security.Cryptography;
using System.Text;

namespace agent.files;

/// <summary>
/// 内容寻址哈希（sha256 十六进制小写）— 备份 blob 名与竞争判定的唯一依据。
/// </summary>
public static class ContentHash
{
    /// <summary>文本内容的 sha256（UTF-8 编码后取哈希）。</summary>
    public static string OfText(string text) => OfBytes(Encoding.UTF8.GetBytes(text));

    /// <summary>字节内容的 sha256。</summary>
    public static string OfBytes(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    /// <summary>取前 len 位做 blob 名（默认 16）。</summary>
    public static string Short(string sha256, int len = 16)
        => sha256.Length <= len ? sha256 : sha256[..len];
}
