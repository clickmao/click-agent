namespace agent.rover.infer;

/// <summary>
/// 逐层 KV cache。布局 = [layer][kvHead][position][dim] —— 把"同一 kv head 的历史位置"放成连续内存,
/// 于是注意力可以直接复用 <c>CpuKernels.AttentionHead</c> (它要求 keys 是 n × headDim 的连续块)。
/// 第 p 个 token 只看 cache 的 [0..p] 段, 因此**单 token 与多 token 走同一条代码路径**,
/// 不存在"只在单 token 下成立"的捷径。容量按需倍增, 不影响已写入位置的语义。
/// </summary>
public sealed class KvCache
{
    private readonly int _nLayer;
    private readonly int _nKvHead;
    private readonly int _kHeadDim;
    private readonly int _vHeadDim;
    private float[][] _k;
    private float[][] _v;

    public int Length { get; private set; }
    public int Capacity { get; private set; }
    public int Layers => _nLayer;
    public int KvHeads => _nKvHead;
    public int KHeadDim => _kHeadDim;
    public int VHeadDim => _vHeadDim;

    public KvCache(int nLayer, int nKvHead, int kHeadDim, int vHeadDim, int initialCapacity)
    {
        if (initialCapacity < 1) throw new ArgumentException("kv_capacity_invalid");
        _nLayer = nLayer;
        _nKvHead = nKvHead;
        _kHeadDim = kHeadDim;
        _vHeadDim = vHeadDim;
        Capacity = initialCapacity;
        _k = new float[nLayer][];
        _v = new float[nLayer][];
        for (int l = 0; l < nLayer; l++)
        {
            _k[l] = new float[(long)nKvHead * Capacity * kHeadDim <= int.MaxValue
                ? nKvHead * Capacity * kHeadDim : throw new ArgumentException("kv_cache_too_large")];
            _v[l] = new float[nKvHead * Capacity * vHeadDim];
        }
    }

    /// <summary>容量不足则整块搬家 (只影响容量, 不改已写入位置的内容)。</summary>
    public void EnsureCapacity(int need)
    {
        if (need <= Capacity) return;
        int cap = Capacity;
        while (cap < need) cap = cap < 1024 ? cap * 2 : cap + cap / 2;
        for (int l = 0; l < _nLayer; l++)
        {
            var nk = new float[_nKvHead * cap * _kHeadDim];
            var nv = new float[_nKvHead * cap * _vHeadDim];
            for (int h = 0; h < _nKvHead; h++)
            {
                Array.Copy(_k[l], h * Capacity * _kHeadDim, nk, h * cap * _kHeadDim, Length * _kHeadDim);
                Array.Copy(_v[l], h * Capacity * _vHeadDim, nv, h * cap * _vHeadDim, Length * _vHeadDim);
            }
            _k[l] = nk;
            _v[l] = nv;
        }
        Capacity = cap;
    }

    /// <summary>把第 layer 层当前 token 的 k/v 写到 cache 尾部 (位置 = Length)。</summary>
    public void Append(int layer, ReadOnlySpan<float> k, ReadOnlySpan<float> v)
    {
        EnsureCapacity(Length + 1);
        if (k.Length < _nKvHead * _kHeadDim) throw new ArgumentException($"kv_k_too_short: {k.Length}");
        if (v.Length < _nKvHead * _vHeadDim) throw new ArgumentException($"kv_v_too_short: {v.Length}");
        for (int h = 0; h < _nKvHead; h++)
        {
            k.Slice(h * _kHeadDim, _kHeadDim)
                .CopyTo(_k[layer].AsSpan((h * Capacity + Length) * _kHeadDim, _kHeadDim));
            v.Slice(h * _vHeadDim, _vHeadDim)
                .CopyTo(_v[layer].AsSpan((h * Capacity + Length) * _vHeadDim, _vHeadDim));
        }
    }

    /// <summary>所有层都 Append 完才推进位置。</summary>
    public void CommitToken() => Length++;

    /// <summary>第 layer 层第 kvHead 个头的前 len 个位置 (连续: len × headDim)</summary>
    public Span<float> Keys(int layer, int kvHead, int len) =>
        _k[layer].AsSpan(kvHead * Capacity * _kHeadDim, len * _kHeadDim);

    public Span<float> Values(int layer, int kvHead, int len) =>
        _v[layer].AsSpan(kvHead * Capacity * _vHeadDim, len * _vHeadDim);

    public void Reset() => Length = 0;

    /// <summary>KV cache 实际占用 (容量口径)</summary>
    public long ResidentBytes
    {
        get
        {
            long per = (long)Capacity * ((long)_nKvHead * _kHeadDim + (long)_nKvHead * _vHeadDim) * 4;
            return per * _nLayer;
        }
    }
}
