using System.Text;

namespace agent.files;

/// <summary>
/// 文本编解码口径（UTF-8 严格）— 非文本（非法字节序列）一律判不可合并，走拒写路径。
/// 写侧不带 BOM（UTF8Encoding(false)），读侧保留原文首字符（含 BOM 若原文件有）。
/// </summary>
public static class TextCodec
{
    private static readonly UTF8Encoding Strict = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    /// <summary>严格解码；失败返回 false（调用方须按「非文本」拒写）。</summary>
    public static bool TryDecode(byte[] bytes, out string text)
    {
        try
        {
            text = Strict.GetString(bytes);
            return true;
        }
        catch (DecoderFallbackException)
        {
            text = string.Empty;
            return false;
        }
    }

    /// <summary>编码（无 BOM）—— 与读取口径成对，保证 round-trip 逐位一致。</summary>
    public static byte[] Encode(string text) => new UTF8Encoding(encoderShouldEmitUTF8Identifier: false).GetBytes(text);
}
