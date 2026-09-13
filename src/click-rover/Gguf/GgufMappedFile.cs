using System.IO.MemoryMappedFiles;

namespace clickrover.gguf;

/// <summary>
/// 只读 mmap 视图 (C2: 惰性加载 / 跨平台 / AOT)。
/// 语义: 文件**不**读进托管堆 — 只建立虚拟地址映射; 页由内核按需调入 (缺页时读盘)。
/// 因此 4.4 GB 模型在 2 GB 内存机器上"能打开"且只触碰真正被访问的张量页 — 这是本引擎的内存前提。
/// 释放: 显式 Dispose (UnmapViewOfFile + 关句柄), 不依赖终结器。
/// </summary>
public sealed unsafe class GgufMappedFile : IDisposable
{
    private MemoryMappedFile? _mmf;
    private MemoryMappedViewAccessor? _view;
    private byte* _ptr;
    private long _length;
    private bool _disposed;

    /// <summary>mmap 命中计数 (惰性加载证据: 每次真正触碰页 → +1; 仅统计元数据/权重窗口取用次数)</summary>
    public long TouchedWindows { get; private set; }

    public long Length => _length;

    public byte* Pointer
    {
        get
        {
            ObjectDisposedException.ThrowIf(_disposed, this);
            return _ptr;
        }
    }

    public static GgufMappedFile Open(string path)
    {
        if (!File.Exists(path))
            throw new FileNotFoundException($"gguf_not_found: {path}", path);

        var f = new GgufMappedFile();
        try
        {
            f._mmf = MemoryMappedFile.CreateFromFile(
                path, FileMode.Open, mapName: null, capacity: 0, MemoryMappedFileAccess.Read);
            f._view = f._mmf.CreateViewAccessor(0, 0, MemoryMappedFileAccess.Read);
            byte* p = null;
            f._view.SafeMemoryMappedViewHandle.AcquirePointer(ref p);
            f._ptr = p;
            f._length = new FileInfo(path).Length;
            return f;
        }
        catch
        {
            f.Dispose();
            throw;
        }
    }

    /// <summary>零拷贝窗口 (不复制字节 — 复制就等于把文件读进内存, 破坏 C2)。</summary>
    public ReadOnlySpan<byte> Window(long offset, int length)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        if (offset < 0 || length < 0 || offset + length > _length)
            throw new ArgumentOutOfRangeException(nameof(offset),
                $"mmap_window_out_of_range: offset={offset} length={length} fileLen={_length}");
        TouchedWindows++;
        return new ReadOnlySpan<byte>(_ptr + offset, length);
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        if (_ptr != null && _view != null)
        {
            try { _view.SafeMemoryMappedViewHandle.ReleasePointer(); } catch { /* 释放期异常不掩盖主流程 */ }
            _ptr = null;
        }
        _view?.Dispose();
        _mmf?.Dispose();
        _view = null;
        _mmf = null;
    }
}
