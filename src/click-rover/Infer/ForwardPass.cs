using System.Diagnostics;
using System.Runtime.InteropServices;
using clickrover.gguf;
using clickrover.quant;
using clickrover.runtime;

namespace clickrover.infer;

/// <summary>逐层回调 (ref struct 只能作为委托参数, 不能作为泛型实参 → 自定义委托类型)</summary>
public delegate void LayerHook(int layer, int tokenIndex, ReadOnlySpan<float> hidden);

/// <summary>单次前向的计时 + 内存读数 (真机证据) 。</summary>
public sealed class ForwardStats
{
    public double OpenMs { get; set; }
    public double EmbedMs { get; set; }
    public double AttnMs { get; set; }
    public double FfnMs { get; set; }
    public double OutNormMs { get; set; }
    public double LmHeadMs { get; set; }
    public double TotalMs { get; set; }
    public double PerTokenMs => TotalMs / Math.Max(1, TokensProcessed);
    public int TokensProcessed { get; set; }
    public long PeakWorkingSetBytes { get; set; }
    public long PeakVmRssBytes { get; set; }
    public long PeakVmHwmBytes { get; set; }
    public double[] LayerMs { get; set; } = Array.Empty<double>();
    public long CachedKvBytes { get; set; }
    /// <summary>本进程从 mmap 窗口"扫过"的量化字节数 (证明逐层流式, 不是全量物化)</summary>
    public long StreamedBytes { get; set; }
}

/// <summary>
/// LLaMA 家族 (含 DeepSeek-Prover-V2-7B) 单/多 token 前向:
///   embed → N × [ RMSNorm → QKV(GEMV) → RoPE → KV cache → GQA 注意力 → O(GEMV) → 残差
///                → RMSNorm → gate/up(GEMV) → SwiGLU → down(GEMV) → 残差 ]
///        → output_norm → lm_head(GEMV) → logits
/// 内存策略: 量化权重**永不物化** —— <see cref="TensorResidency.StreamWindow"/> 取零拷贝窗口,
/// <see cref="CpuKernels.Gemv"/> 在块内反量化后立即点积 (块缓冲只有 256 个 float)。
/// 因此峰值额外内存 ≈ 激活 + KV cache (与 4.22 GB 权重规模无关)。
/// </summary>
public sealed unsafe class ForwardPass : IDisposable
{
    private const int MadvDontNeed = 4;

    [DllImport("libc", EntryPoint = "madvise", SetLastError = true)]
    private static extern int Madvise(nint addr, nuint length, int advice);

    private readonly GgufReader _r;
    private readonly ModelConfig _c;
    private readonly TensorResidency _res;
    private readonly RopeTable _rope;
    private readonly KvCache _cache;
    private readonly bool _dropPages;
    /// <summary>每个 token 后主动释放非常驻物化张量 (主动回收入口; 默认关, 以免热 norm 反复重解量化)</summary>
    private readonly bool _reclaimPerToken;

    private readonly float[] _x, _xn, _q, _k, _v, _attn, _proj, _ff, _gate, _up, _logits, _scores;
    private readonly float[]? _qBias, _kBias, _vBias, _oBias;

    public ModelConfig Config => _c;
    public ResidencyLedger Ledger => _res.Ledger;
    public KvCache Cache => _cache;
    /// <summary>当前物化常驻张量数 (驻留账读数; 量化权重走流窗口不计入)</summary>
    public int ResidentCount => _res.ResidentCount;
    public ForwardStats Stats { get; } = new();

    public ForwardPass(GgufReader r, ModelConfig c, int maxPositions, long budgetBytes, bool dropPages,
        IReadOnlyCollection<string>? pins = null, bool reclaimPerToken = false)
    {
        _r = r; _c = c; _dropPages = dropPages; _reclaimPerToken = reclaimPerToken;

        // 热集口径: pins == null ⇒ 默认钉住全部 norm (每层每 token 必用, 活性最高);
        // pins 显式给出 (含空集) ⇒ 用调用方口径: 空集 = 不预判热集, 全交给预算 + LRU,
        // 驱逐路径因此**真被触发** (账面有 evicts/reclaimed 数字, 不靠调用方相信)。
        IReadOnlyCollection<string> pinned;
        if (pins is null)
        {
            var def = new List<string>();
            for (int l = 0; l < c.NLayer; l++)
            {
                def.Add($"blk.{l}.attn_norm.weight");
                def.Add($"blk.{l}.ffn_norm.weight");
            }
            def.Add("output_norm.weight");
            pinned = def;
        }
        else pinned = pins;

        _qBias = MaybeLoadBias("attn_q.bias", c.QElems);
        _kBias = MaybeLoadBias("attn_k.bias", c.KvElems);
        _vBias = MaybeLoadBias("attn_v.bias", c.KvElems);
        _oBias = MaybeLoadBias("attn_output.bias", c.Hidden);

        if (c.HeadDim != c.ValueDim)
            throw new NotSupportedException($"v_dim_differs_from_k_dim_unsupported: k={c.HeadDim} v={c.ValueDim}");
        _res = new TensorResidency(r, budgetBytes, pinned);
        _rope = new RopeTable(c.RopeDim, c.RopeBase, c.RopeScaling, c.RopeFactor, maxPositions);
        // KV cache 容量按需增长: 初值取 min(ctx, 8), 不预分配整个上下文
        _cache = new KvCache(c.NLayer, c.NHeadKv, c.HeadDim, c.ValueDim, Math.Min(maxPositions, 8));

        _x = new float[c.Hidden];
        _xn = new float[c.Hidden];
        _q = new float[c.QElems];
        _k = new float[c.KvElems];
        _v = new float[c.KvElems];
        _attn = new float[c.QElems];
        _proj = new float[c.Hidden];
        _ff = new float[c.Ffn];
        _gate = new float[c.Ffn];
        _up = new float[c.Ffn];
        _logits = new float[c.Vocab];
        _scores = new float[maxPositions];

        Stats.LayerMs = new double[c.NLayer];
        Stats.CachedKvBytes = _cache.ResidentBytes;
    }

    /// <summary>可选 bias 张量 (本模型无): 有则物化成托管数组; 只看第 0 层, 但要求所有层都存在 (避免层间不一致)。</summary>
    private float[]? MaybeLoadBias(string suffix, int len)
    {
        var t = _r.Find("blk.0." + suffix);
        if (t is null) return null;
        if (t.Dims.Length != 1 || t.Dims[0] != len)
            throw new InvalidDataException($"cfg_shape_mismatch: blk.0.{suffix} dims=[{string.Join(",", t.Dims)}] expect=[{len}]");
        for (int l = 0; l < _c.NLayer; l++)
            if (_r.Find($"blk.{l}.{suffix}") is null)
                throw new InvalidDataException($"cfg_missing_tensor: blk.{l}.{suffix}");
        using var tmp = new TensorResidency(_r, 0, new[] { "blk.0." + suffix });
        return tmp.AcquireF32("blk.0." + suffix).Span.ToArray();
    }

    /// <summary>量化权重 × 向量 (零拷贝 mmap 窗口 + 块内融合反量化), 可选加 bias。</summary>
    private void Gemv(string name, int rows, int cols, ReadOnlySpan<float> x, Span<float> y, float[]? bias)
    {
        var t = _r.Require(name);
        if (t.Dims.Length != 2 || t.Dims[0] != cols || t.Dims[1] != rows)
            throw new InvalidDataException($"gemv_shape_mismatch: {name} dims=[{string.Join(",", t.Dims)}] expect=[{cols},{rows}]");
        var w = _res.StreamWindow(name);
        CpuKernels.Gemv(t.Type, w, rows, cols, x, y);
        if (bias is not null)
            for (int i = 0; i < rows; i++) y[i] += bias[i];
        DropPages(t);
    }

    private Span<float> NormWeight(string name)
    {
        var b = _res.AcquireF32(name);
        if (b.Length != _c.Hidden) throw new InvalidDataException($"norm_len_mismatch: {name} {b.Length} != {_c.Hidden}");
        return b.Span;
    }

    /// <summary>token 嵌入: 只反量化被选中的那一行 (词表 10 万 × 4096, 单行 9 KiB)。</summary>
    private void Embed(int token, Span<float> dst)
    {
        if (token < 0 || token >= _c.Vocab) throw new ArgumentOutOfRangeException(nameof(token), $"token_out_of_range: {token} vocab={_c.Vocab}");
        var t = _r.Require("token_embd.weight");
        var w = _res.StreamWindow("token_embd.weight");
        Dequant.RowAt(t.Type, w, token, _c.Hidden, dst);
        DropPages(t);
    }

    /// <summary>算完即放页: madvise(MADV_DONTNEED) 让内核立刻回收该张量的文件页 (RSS 不随层数累积)。</summary>
    private void DropPages(GgufTensorInfo t)
    {
        if (!_dropPages) return;
        long off = _r.DataSectionOffset + t.Offset;
        long pageStart = off & ~4095L;
        long end = off + t.ByteSize;
        long len = ((end + 4095L) & ~4095L) - pageStart;
        if (len <= 0) return;
        Madvise((nint)(_r.Mapped.Pointer + pageStart), (nuint)len, MadvDontNeed);
    }

    /// <summary>多层前向 (自回归: 每个 token 只看 ≤ 自身位置的 KV cache)。返回最后一个 token 的 logits。</summary>
    public float[] Forward(IReadOnlyList<int> tokens, TextWriter? log = null, LayerHook? afterLayer = null)
    {
        if (tokens.Count == 0) throw new ArgumentException("forward_no_tokens");
        if (tokens.Count > _rope.MaxPositions) throw new ArgumentException($"forward_tokens_exceed_rope: {tokens.Count} > {_rope.MaxPositions}");
        _cache.EnsureCapacity(tokens.Count);

        var swTotal = Stopwatch.StartNew();
        double embedMs = 0, attnMs = 0, ffnMs = 0, outNormMs = 0, lmHeadMs = 0;

        for (int ti = 0; ti < tokens.Count; ti++)
        {
            int pos = _cache.Length;
            if (pos >= _rope.MaxPositions) throw new ArgumentException($"forward_pos_exceed_ctx: {pos}");

            var sw = Stopwatch.StartNew();
            Embed(tokens[ti], _x);
            embedMs += sw.Elapsed.TotalMilliseconds;

            for (int l = 0; l < _c.NLayer; l++)
            {
                string p = _c.LayerPrefix(l);
                sw.Restart();
                // ---- 注意力 ----
                var an = NormWeight(p + "attn_norm.weight");
                CpuKernels.RmsNorm(_x, an, _c.RmsEps, _xn);
                Gemv(p + "attn_q.weight", _c.QElems, _c.Hidden, _xn, _q, _qBias);
                Gemv(p + "attn_k.weight", _c.KvElems, _c.Hidden, _xn, _k, _kBias);
                Gemv(p + "attn_v.weight", _c.KvElems, _c.Hidden, _xn, _v, _vBias);
                _rope.Apply(_q, _c.NHead, _c.HeadDim, pos);
                _rope.Apply(_k, _c.NHeadKv, _c.HeadDim, pos);
                _cache.Append(l, _k, _v);

                int n = pos + 1;
                for (int h = 0; h < _c.NHead; h++)
                {
                    int kvh = h / _c.GqaGroup;   // GQA: 相邻 nHead/nHeadKv 个 query head 共享一个 kv head
                    CpuKernels.AttentionHead(
                        _q.AsSpan(h * _c.HeadDim, _c.HeadDim),
                        _cache.Keys(l, kvh, n), _cache.Values(l, kvh, n),
                        n, _c.HeadDim, _c.AttnScale, _scores, _attn.AsSpan(h * _c.HeadDim, _c.HeadDim));
                }
                Gemv(p + "attn_output.weight", _c.Hidden, _c.QElems, _attn, _proj, _oBias);
                CpuKernels.AddInPlace(_x, _proj);

                // ---- SwiGLU FFN ----
                double attnPart = sw.Elapsed.TotalMilliseconds;
                var fn = NormWeight(p + "ffn_norm.weight");
                CpuKernels.RmsNorm(_x, fn, _c.RmsEps, _xn);
                Gemv(p + "ffn_gate.weight", _c.Ffn, _c.Hidden, _xn, _gate, null);
                Gemv(p + "ffn_up.weight", _c.Ffn, _c.Hidden, _xn, _up, null);
                CpuKernels.SwiGlu(_gate, _up, _ff);
                Gemv(p + "ffn_down.weight", _c.Hidden, _c.Ffn, _ff, _xn.AsSpan(0, _c.Hidden), null);
                CpuKernels.AddInPlace(_x, _xn.AsSpan(0, _c.Hidden));
                sw.Stop();

                attnMs += attnPart;
                ffnMs += sw.Elapsed.TotalMilliseconds - attnPart;
                Stats.LayerMs[l] += sw.Elapsed.TotalMilliseconds;
                afterLayer?.Invoke(l, ti, _x);
            }

            _cache.CommitToken();
            if (_reclaimPerToken) _res.ReclaimAll();   // 主动释放: 本 token 物化的非常驻张量已不再需要
            SampleMemory();
            if (log is not null)
                log.WriteLine($"step{{token_index={ti} token={tokens[ti]} pos={pos} kv_len={_cache.Length} " +
                              $"cache_bytes={_cache.ResidentBytes} resident={_res.ResidentCount} " +
                              $"reclaimed_bytes={Ledger.ReclaimedBytes} evicts={Ledger.EvictCount} " +
                              $"layer_ms_sum={Stats.LayerMs.Sum():F1}}}");
        }

        swTotal.Stop();
        double preLm = swTotal.Elapsed.TotalMilliseconds;

        var swLm = Stopwatch.StartNew();
        var on = NormWeight("output_norm.weight");
        CpuKernels.RmsNorm(_x, on, _c.RmsEps, _xn);
        outNormMs += swLm.Elapsed.TotalMilliseconds;
        swLm.Restart();
        string headName = _c.HasOutputTensor ? "output.weight" : "token_embd.weight";
        Gemv(headName, _c.Vocab, _c.Hidden, _xn, _logits, null);
        lmHeadMs += swLm.Elapsed.TotalMilliseconds;

        SampleMemory();
        Stats.EmbedMs = embedMs;
        Stats.AttnMs = attnMs;
        Stats.FfnMs = ffnMs;
        Stats.OutNormMs = outNormMs;
        Stats.LmHeadMs = lmHeadMs;
        Stats.TotalMs = preLm + lmHeadMs;
        Stats.TokensProcessed = tokens.Count;
        Stats.StreamedBytes = Ledger.StreamedBytes;
        Stats.CachedKvBytes = _cache.ResidentBytes;
        return _logits;
    }

    /// <summary>top-k (k 很小, 单趟部分选择; 同分按 id 升序, 确定性)</summary>
    public static (int Id, float Logit)[] TopK(float[] logits, int k)
    {
        var best = new List<(int, float)>(k);
        for (int i = 0; i < logits.Length; i++)
        {
            float v = logits[i];
            if (best.Count == k && v <= best[^1].Item2) continue;
            int at = best.Count;
            while (at > 0 && best[at - 1].Item2 < v) at--;
            best.Insert(at, (i, v));
            if (best.Count > k) best.RemoveAt(k);
        }
        return best.ToArray();
    }

    private void SampleMemory()
    {
        long ws = 0;
        using (var p = Process.GetCurrentProcess()) { p.Refresh(); ws = p.WorkingSet64; }
        var (rss, hwm) = ReadVm();
        if (ws > Stats.PeakWorkingSetBytes) Stats.PeakWorkingSetBytes = ws;
        if (rss > Stats.PeakVmRssBytes) Stats.PeakVmRssBytes = rss;
        if (hwm > Stats.PeakVmHwmBytes) Stats.PeakVmHwmBytes = hwm;
    }

    public static (long VmRss, long VmHwm) ReadVm()
    {
        long rss = 0, hwm = 0;
        try
        {
            foreach (var line in File.ReadLines("/proc/self/status"))
            {
                if (line.StartsWith("VmRSS:", StringComparison.Ordinal)) rss = ParseKb(line);
                else if (line.StartsWith("VmHWM:", StringComparison.Ordinal)) hwm = ParseKb(line);
            }
        }
        catch (IOException) { /* /proc 不可读时留 0, 不编造 */ }
        return (rss, hwm);
    }

    private static long ParseKb(string line)
    {
        var parts = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        return parts.Length >= 2 && long.TryParse(parts[1], out var kb) ? kb * 1024 : 0;
    }

    public void Dispose() => _res.Dispose();
}
