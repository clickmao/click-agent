// R480: 独立文本召回模块 —— 只读 IO / 计数 / 异常。
// 设计要点: 一律 pread(RandomAccess) 语义按需读取, 不 mmap 整索引 ⇒
//   进程常驻内存 ≠ 索引体积 (页缓存由内核拥有, 不计入本模块常驻面)。
using Microsoft.Win32.SafeHandles;

namespace agent.recall;

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
