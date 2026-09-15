// R480: 独立文本召回模块 —— 只读 IO / 计数 / 异常。
// 设计要点: 一律 pread(RandomAccess) 语义按需读取, 不 mmap 整索引 ⇒
//   进程常驻内存 ≠ 索引体积 (页缓存由内核拥有, 不计入本模块常驻面)。
using Microsoft.Win32.SafeHandles;

namespace agent.Recall;

public sealed class RecallCorruptionException : Exception
{
    public RecallCorruptionException(string message) : base(message) { }
}

public sealed class RecallFormatException : Exception
{
    public RecallFormatException(string message) : base(message) { }
}

/// <summary>读取计数: 用于把「几十 ms」拆成 syscall 次数 + 字节量, 而不是只报一个墙钟。</summary>
public sealed class RecallReadStats
{
    public long Reads;
    public long BytesRead;
    public long TermLookups;
    public long BlocksScanned;
    public long BlocksSkipped;
    public long PostingsVisited;
    public long DocsScored;

    public void Reset()
    {
        Reads = 0;
        BytesRead = 0;
        TermLookups = 0;
        BlocksScanned = 0;
        BlocksSkipped = 0;
        PostingsVisited = 0;
        DocsScored = 0;
    }

    /// <summary>记一次 ad-hoc pread (链接表/正文等按需读取也计入器具口径)。</summary>
    public void CountRead(int bytes)
    {
        Reads++;
        BytesRead += bytes;
    }

    public RecallReadStats Snapshot() => new()
    {
        Reads = Reads,
        BytesRead = BytesRead,
        TermLookups = TermLookups,
        BlocksScanned = BlocksScanned,
        BlocksSkipped = BlocksSkipped,
        PostingsVisited = PostingsVisited,
        DocsScored = DocsScored,
    };
}

/// <summary>只读文件句柄 (pread)。任何短读一律 fail-closed, 不返回静默零值。</summary>
public sealed class RecallFile : IDisposable
{
    public string Path { get; }
    public long Length { get; }

    private readonly SafeFileHandle _handle;
    private readonly RecallReadStats? _stats;

    public RecallFile(string path, RecallReadStats? stats = null)
    {
        Path = path;
        _stats = stats;
        _handle = File.OpenHandle(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        Length = RandomAccess.GetLength(_handle);
    }

    public void ReadExactly(long offset, Span<byte> dst)
    {
        if (offset < 0 || offset + dst.Length > Length)
        {
            throw new RecallCorruptionException($"read out of range: off={offset} len={dst.Length} file={Path} size={Length}");
        }
        long pos = offset;
        int done = 0;
        while (done < dst.Length)
        {
            int n = RandomAccess.Read(_handle, dst.Slice(done), pos + done);
            if (n <= 0)
            {
                throw new RecallCorruptionException($"short read: off={pos + done} file={Path}");
            }
            done += n;
        }
        if (_stats is not null)
        {
            _stats.Reads++;
            _stats.BytesRead += dst.Length;
        }
    }

    public byte[] ReadBytes(long offset, int length)
    {
        var buf = new byte[length];
        ReadExactly(offset, buf);
        return buf;
    }

    /// <summary>顺序读一段到缓冲, 返回实际读到的字节数 (用于分流式扫描大文件)。</summary>
    public int ReadUpTo(long offset, Span<byte> dst)
    {
        if (offset >= Length)
        {
            return 0;
        }
        int want = (int)Math.Min(dst.Length, Length - offset);
        int done = 0;
        while (done < want)
        {
            int n = RandomAccess.Read(_handle, dst.Slice(done, want - done), offset + done);
            if (n <= 0)
            {
                break;
            }
            done += n;
        }
        if (_stats is not null)
        {
            _stats.Reads++;
            _stats.BytesRead += done;
        }
        return done;
    }

    public void Dispose() => _handle.Dispose();
}

/// <summary>常驻内存账本: 每一条都必须能被源码事实对上, 空白声明不算数。</summary>
public sealed class RecallMemoryReport
{
    private readonly List<(string Name, long Bytes)> _items = new();

    public void Add(string name, long bytes) => _items.Add((name, bytes));

    public long TotalBytes
    {
        get
        {
            long t = 0;
            for (int i = 0; i < _items.Count; i++)
            {
                t += _items[i].Bytes;
            }
            return t;
        }
    }

    public IReadOnlyList<(string Name, long Bytes)> Items => _items;

    public string Describe()
    {
        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < _items.Count; i++)
        {
            sb.Append(_items[i].Name).Append('=').Append(_items[i].Bytes).Append(' ');
        }
        sb.Append("total=").Append(TotalBytes);
        return sb.ToString();
    }
}
