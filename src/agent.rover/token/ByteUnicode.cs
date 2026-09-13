namespace agent.rover.token;

/// <summary>
/// GPT-2 bytes_to_unicode 映射 (与 HF ByteLevel 预分词/解码器同构):
/// 把 256 个字节一一映射到可打印 Unicode 字符, 使任意 UTF-8 字节串可被 BPE 词表表示。
/// 编码方向 字节→字符 (预分词末步); 解码方向 字符→字节 (解码器首步)。
/// </summary>
public static class ByteUnicode
{
    /// <summary>字节 → 可打印字符, 下标即字节值 (恒 256 项)。</summary>
    private static readonly char[] ToChars = BuildToChars();

    /// <summary>可打印字符 → 字节, 下标为 UTF-16 码元; -1 表示不在表内。</summary>
    private static readonly short[] ToBytes = BuildToBytes(ToChars);

    /// <summary>表项数 (恒 256, 供自检)。</summary>
    public const int TableSize = 256;

    public static char ToChar(byte b) => ToChars[b];

    /// <summary>字符 → 字节。不在表内的字符 (如特殊符号里的 U+2581) 返回 false。</summary>
    public static bool TryToByte(char c, out byte b)
    {
        short v = ToBytes[c];
        b = v < 0 ? (byte)0 : (byte)v;
        return v >= 0;
    }

    /// <summary>UTF-8 字节 → 可打印字符序列 (ByteLevel 预分词末步)。</summary>
    public static string Encode(string text)
    {
        int n = System.Text.Encoding.UTF8.GetByteCount(text);
        if (n == 0)
        {
            return string.Empty;
        }

        byte[] buf = new byte[n];
        System.Text.Encoding.UTF8.GetBytes(text, buf);
        char[] chars = new char[n];
        for (int i = 0; i < n; i++)
        {
            chars[i] = ToChars[buf[i]];
        }

        return new string(chars);
    }

    /// <summary>可打印字符序列 → 原始字节 (解码器首步)。不在表内的字符按其 UTF-8 字节追加。</summary>
    public static void AppendBytes(string piece, List<byte> dst)
    {
        foreach (char c in piece)
        {
            if (TryToByte(c, out byte b))
            {
                dst.Add(b);
            }
            else if (char.IsSurrogate(c))
            {
                // 代理对单独处理: 按 UTF-8 原样追加, 与 Rust from_utf8_lossy 语义一致。
                dst.AddRange(System.Text.Encoding.UTF8.GetBytes(c.ToString()));
            }
            else
            {
                dst.AddRange(System.Text.Encoding.UTF8.GetBytes(c.ToString()));
            }
        }
    }

    /// <summary>表结构性自检: 256 项双射 (值域不重合、可逆)。</summary>
    public static bool SelfCheck(out string detail)
    {
        for (int b = 0; b < TableSize; b++)
        {
            char c = ToChars[b];
            if (!TryToByte(c, out byte back) || back != (byte)b)
            {
                detail = $"byte 0x{b:X2} → U+{(int)c:X4} 反查失败";
                return false;
            }
        }

        HashSet<char> uniq = new(ToChars);
        if (uniq.Count != TableSize)
        {
            detail = $"映射非双射: 不同字符 {uniq.Count} 个";
            return false;
        }

        detail = $"256 项双射 (bytes 33-126/161-172/174-255 恒等, 其余 → U+0100..)";
        return true;
    }

    private static char[] BuildToChars()
    {
        List<int> bs = new(TableSize);
        for (int b = 0x21; b <= 0x7E; b++)
        {
            bs.Add(b);
        }

        for (int b = 0xA1; b <= 0xAC; b++)
        {
            bs.Add(b);
        }

        for (int b = 0xAE; b <= 0xFF; b++)
        {
            bs.Add(b);
        }

        List<int> cs = new(bs);
        int n = 0;
        for (int b = 0; b < TableSize; b++)
        {
            if (!bs.Contains(b))
            {
                bs.Add(b);
                cs.Add(TableSize + n);
                n++;
            }
        }

        char[] map = new char[TableSize];
        for (int i = 0; i < bs.Count; i++)
        {
            map[bs[i]] = (char)cs[i];
        }

        return map;
    }

    private static short[] BuildToBytes(char[] toChars)
    {
        short[] map = new short[char.MaxValue + 1];
        Array.Fill(map, (short)-1);
        for (int b = 0; b < toChars.Length; b++)
        {
            map[toChars[b]] = (short)b;
        }

        return map;
    }
}
