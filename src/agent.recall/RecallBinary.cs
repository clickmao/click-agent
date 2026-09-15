// R480: 独立文本召回模块 —— 二进制编解码原语 (零反射 / AOT 安全 / 纯 BCL)。
// 通用代码逻辑: 这里只有「整数变长编码 + 有界缓冲」, 不含任何具体语言或业务分支。
namespace agent.Recall;

/// <summary>无符号 LEB128 变长整数。所有偏移/长度/delta 一律用它, 索引体积与 docId 基数脱钩。</summary>
internal static class VarInt
{
    public const int MaxBytes64 = 10;
    public const int MaxBytes32 = 5;

    public static int Write(Span<byte> dst, ulong value)
    {
        int i = 0;
        while (value >= 0x80)
        {
            dst[i++] = (byte)(value | 0x80);
            value >>= 7;
        }
        dst[i++] = (byte)value;
        return i;
    }

    public static int Size(ulong value)
    {
        int n = 1;
        while (value >= 0x80)
        {
            value >>= 7;
            n++;
        }
        return n;
    }

    public static void WriteTo(Stream s, ulong value)
    {
        Span<byte> tmp = stackalloc byte[MaxBytes64];
        int n = Write(tmp, value);
        s.Write(tmp[..n]);
    }

    /// <summary>从 span 读一个 varint；返回消耗的字节数, 0 表示越界(调用方必须 fail-closed)。</summary>
    public static int Read(ReadOnlySpan<byte> src, out ulong value)
    {
        value = 0;
        int shift = 0;
        for (int i = 0; i < src.Length && i < MaxBytes64; i++)
        {
            byte b = src[i];
            value |= (ulong)(b & 0x7F) << shift;
            if ((b & 0x80) == 0)
            {
                return i + 1;
            }
            shift += 7;
        }
        return 0;
    }
}

/// <summary>只增不减的字节缓冲; 用于按 docId 递增顺序在线写出 delta 编码的 postings。</summary>
internal sealed class ByteBuffer
{
    private byte[] _buf;
    private int _len;

    public ByteBuffer(int capacity = 256)
    {
        _buf = new byte[capacity < 16 ? 16 : capacity];
        _len = 0;
    }

    public int Length => _len;
    public ReadOnlySpan<byte> Span => _buf.AsSpan(0, _len);
    public byte[] Raw => _buf;

    public void EnsureCapacity(int extra)
    {
        int need = _len + extra;
        if (need <= _buf.Length)
        {
            return;
        }
        int cap = _buf.Length;
        while (cap < need)
        {
            cap = cap < 1024 ? cap * 4 : cap * 2;
        }
        Array.Resize(ref _buf, cap);
    }

    public void WriteByte(byte b)
    {
        EnsureCapacity(1);
        _buf[_len++] = b;
    }

    public void Write(ReadOnlySpan<byte> src)
    {
        EnsureCapacity(src.Length);
        src.CopyTo(_buf.AsSpan(_len));
        _len += src.Length;
    }

    public void WriteVarInt(ulong value)
    {
        EnsureCapacity(VarInt.MaxBytes64);
        _len += VarInt.Write(_buf.AsSpan(_len), value);
    }

    public void Clear() => _len = 0;

    public void CopyTo(Stream s) => s.Write(_buf, 0, _len);
}
