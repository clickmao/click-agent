namespace agent.recall;


/// <summary>顺序流式读 (小窗口 + 逐字节 varint), 让指纹表读取不随文件数增长。</summary>
internal sealed class RecallSequentialReader : IDisposable
{
    private const int WindowBytes = 64 * 1024;
    private readonly RecallFile _file;
    private readonly byte[] _win = new byte[WindowBytes];
    private long _pos;
    private int _len;
    private int _idx;

    public RecallSequentialReader(string path)
    {
        _file = new RecallFile(path, null);
    }

    public bool TryReadByte(out byte b)
    {
        if (_idx >= _len)
        {
            _len = _file.ReadUpTo(_pos, _win);
            _pos += _len;
            _idx = 0;
            if (_len <= 0)
            {
                b = 0;
                return false;
            }
        }
        b = _win[_idx++];
        return true;
    }

    public bool TryReadVarInt(out ulong value)
    {
        value = 0;
        int shift = 0;
        while (shift < 70)
        {
            if (!TryReadByte(out byte b))
            {
                return false;
            }
            value |= (ulong)(b & 0x7F) << shift;
            if ((b & 0x80) == 0)
            {
                return true;
            }
            shift += 7;
        }
        return false;
    }

    public bool TryReadBytes(int count, out byte[] dst)
    {
        dst = new byte[count];
        for (int i = 0; i < count; i++)
        {
            if (!TryReadByte(out byte b))
            {
                return false;
            }
            dst[i] = b;
        }
        return true;
    }

    public void Dispose() => _file.Dispose();
}
