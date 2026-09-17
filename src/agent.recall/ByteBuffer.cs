namespace agent.recall;


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
