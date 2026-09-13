using System.Runtime.InteropServices;
using clickrover.gguf;
using clickrover.quant;

namespace clickrover.runtime;

/// <summary>
/// 驻留账 (C3 证据载体): 每次加载/释放/回收都有字节数, 结束时可打印 →
/// "只常驻活性高的张量 + 主动释放" 不是口号, 是有账面数字的可核事实。
/// </summary>
public sealed class ResidencyLedger
{
    public long LoadedBytes { get; internal set; }
    public long ReclaimedBytes { get; internal set; }
    public long StreamedBytes { get; internal set; }
    public long LoadCount { get; internal set; }
    public long EvictCount { get; internal set; }
    public long ReclaimCount { get; internal set; }
    public long CacheHits { get; internal set; }
    public long CacheMisses { get; internal set; }
    public long PeakResidentBytes { get; internal set; }
    public long BudgetBytes { get; internal set; }

    public double HitRate => CacheHits + CacheMisses == 0 ? 0 : (double)CacheHits / (CacheHits + CacheMisses);

    public IEnumerable<string> Lines()
    {
        yield return $"residency{{loaded={Fmt(LoadedBytes)} reclaimed={Fmt(ReclaimedBytes)} streamed={Fmt(StreamedBytes)}}}";
        yield return $"residency{{loads={LoadCount} evicts={EvictCount} reclaims={ReclaimCount} hits={CacheHits} misses={CacheMisses} hit_rate={HitRate:P2}}}";
        yield return $"residency{{peak_resident={Fmt(PeakResidentBytes)} budget={Fmt(BudgetBytes)}}}";
    }

    internal static string Fmt(long bytes) => bytes >= 1 << 20 ? $"{bytes / 1048576.0:F1}MiB" : $"{bytes / 1024.0:F1}KiB";
}

/// <summary>显式释放的原生张量缓冲 (不进 GC 堆 → 释放确定, 无终结器延迟)</summary>
public sealed unsafe class TensorBuffer : IDisposable
{
    private readonly string _name;
    private float* _ptr;
    public int Length { get; }
    /// <summary>true = 常驻 (热集), 不参与 LRU 驱逐</summary>
    public bool Pinned { get; internal set; }
    internal long LastUseTick { get; set; }
    internal TensorResidency? Owner { get; init; }

    public long Bytes => (long)Length * 4;

    internal TensorBuffer(string name, int length, float* ptr)
    {
        _name = name;
        Length = length;
        _ptr = ptr;
    }

    public Span<float> Span
    {
        get
        {
            if (_ptr == null) throw new ObjectDisposedException($"tensor_buffer_released: {_name}");
            return new Span<float>(_ptr, Length);
        }
    }

    public string Name => _name;

    public void Dispose()
    {
        if (_ptr == null) return;
        Owner?.OnBufferDisposed(this);
        _ptr = null;
    }

    internal void FreeNative()
    {
        if (_ptr == null) return;
        NativeMemory.AlignedFree(_ptr);
        _ptr = null;
    }
}

/// <summary>
/// 张量驻留管理器 (C2+C3 落点):
///  · 量化权重: **永不物化** — <see cref="StreamWindow"/> 直接从 mmap 零拷贝取窗口, 融合进矩阵乘;
///  · 常用小张量 (norm/embedding/输出头等"活性高"的): <see cref="AcquireF32"/> 物化并常驻 (Pinned);
///  · 其余物化张量: LRU, 超预算或显式 <see cref="ReclaimAll"/> 时**主动** NativeMemory.Free。
/// </summary>
public sealed class TensorResidency : IDisposable
{
    private readonly GgufReader _reader;
    private readonly Dictionary<string, TensorBuffer> _resident = new(StringComparer.Ordinal);
    private readonly Dictionary<string, long> _lastUse = new(StringComparer.Ordinal);
    private readonly HashSet<string> _pinned;
    private readonly int _hotThreshold;
    private long _tick;
    private bool _disposed;

    public ResidencyLedger Ledger { get; } = new();

    public TensorResidency(GgufReader reader, long budgetBytes, IEnumerable<string>? pinned = null, int hotAccessThreshold = 2)
    {
        _reader = reader;
        _pinned = new HashSet<string>(pinned ?? Array.Empty<string>(), StringComparer.Ordinal);
        _hotThreshold = hotAccessThreshold;
        Ledger.BudgetBytes = budgetBytes;
    }

    public int ResidentCount => _resident.Count;
    public long ResidentBytes => _resident.Values.Sum(b => b.Bytes);
    public IReadOnlyCollection<string> PinnedNames => _pinned;

    /// <summary>热集: 显式 pin ∪ 访问次数达阈值的张量 (活性判据是访问计数, 不是猜测)</summary>
    public bool IsHot(string name) => _pinned.Contains(name) || AccessCount(name) >= _hotThreshold;

    private readonly Dictionary<string, long> _access = new(StringComparer.Ordinal);
    public long AccessCount(string name) => _access.TryGetValue(name, out var c) ? c : 0;

    /// <summary>mmap 零拷贝窗口 (量化权重路径): 不物化、不计驻留, 只计触碰字节</summary>
    public ReadOnlySpan<byte> StreamWindow(string tensorName)
    {
        var t = _reader.Require(tensorName);
        var w = _reader.TensorWindow(t);
        Ledger.StreamedBytes += w.Length;
        return w;
    }

    /// <summary>物化 F32 副本并纳入驻留管理 (小张量/需全量参与运算者)</summary>
    public unsafe TensorBuffer AcquireF32(string tensorName)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        Bump(tensorName);
        if (_resident.TryGetValue(tensorName, out var existing))
        {
            Ledger.CacheHits++;
            existing.LastUseTick = ++_tick;
            return existing;
        }
        Ledger.CacheMisses++;

        var info = _reader.Require(tensorName);
        if (info.ElementCount > int.MaxValue) throw new NotSupportedException($"tensor_too_large: {tensorName}");
        int n = (int)info.ElementCount;
        float* ptr = (float*)NativeMemory.AlignedAlloc((nuint)((long)n * 4), 64);
        try
        {
            var dst = new Span<float>(ptr, n);
            Dequant.Row(info.Type, _reader.TensorWindow(info), dst, n);
        }
        catch
        {
            NativeMemory.AlignedFree(ptr);
            throw;
        }

        var buf = new TensorBuffer(tensorName, n, ptr) { Owner = this, Pinned = _pinned.Contains(tensorName) };
        buf.LastUseTick = ++_tick;
        _resident[tensorName] = buf;
        Ledger.LoadedBytes += buf.Bytes;
        Ledger.LoadCount++;
        if (ResidentBytes > Ledger.PeakResidentBytes) Ledger.PeakResidentBytes = ResidentBytes;
        EnforceBudget(tensorName);
        return buf;
    }

    private void Bump(string name)
    {
        _access[name] = AccessCount(name) + 1;
        _lastUse[name] = ++_tick;
    }

    internal void OnBufferDisposed(TensorBuffer buf)
    {
        if (_resident.TryGetValue(buf.Name, out var cur) && ReferenceEquals(cur, buf))
            _resident.Remove(buf.Name);
        buf.FreeNative();
        Ledger.ReclaimedBytes += buf.Bytes;
        Ledger.ReclaimCount++;
    }

    /// <summary>显式回收: 释放全部非常驻张量 (返回回收字节)。这是"主动从内存释放"的入口。</summary>
    public long ReclaimAll()
    {
        long freed = 0;
        foreach (var name in _resident.Keys.ToList())
        {
            var b = _resident[name];
            if (b.Pinned) continue;
            freed += b.Bytes;
            b.Dispose();
        }
        return freed;
    }

    /// <summary>超预算时按 LRU 驱逐非常驻张量 (最近最少用先走)</summary>
    private void EnforceBudget(string incoming)
    {
        if (Ledger.BudgetBytes <= 0) return;
        while (ResidentBytes > Ledger.BudgetBytes)
        {
            string? victim = null;
            long oldest = long.MaxValue;
            foreach (var kv in _resident)
            {
                if (kv.Value.Pinned || kv.Key == incoming) continue;
                if (kv.Value.LastUseTick < oldest) { oldest = kv.Value.LastUseTick; victim = kv.Key; }
            }
            if (victim == null) break; // 只剩 pin 的 → 不再驱逐 (如实停手, 不假驱逐)
            var vb = _resident[victim];
            Ledger.EvictCount++;
            vb.Dispose();
        }
    }

    /// <summary>当前进程内存读数 (真机证据用)</summary>
    public static (long ManagedBytes, long WorkingSetBytes) MemorySnapshot()
    {
        using var p = System.Diagnostics.Process.GetCurrentProcess();
        p.Refresh();
        return (GC.GetTotalMemory(false), p.WorkingSet64);
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        foreach (var b in _resident.Values.ToList()) b.Dispose();
        _resident.Clear();
    }
}
