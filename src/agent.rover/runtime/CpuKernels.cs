using System.Numerics.Tensors;
using agent.rover.gguf;
using agent.rover.infer;
using agent.rover.quant;

namespace agent.rover.runtime;

/// <summary>
/// CPU 内核 (C5 的 CPU 侧): 全部基于 <see cref="TensorPrimitives"/> / 标量块循环 → 跨平台 + AOT 安全。
/// 关键设计: 量化权重**融合**参与矩阵乘 (块内反量化到栈缓冲即刻点积), 不物化整行/整张量 →
/// 峰值内存与"张量字节数"无关, 只与块大小 (256 元素) 相关。这是 C3 内存回收成立的前提。
/// </summary>
public static class CpuKernels
{
    /// <summary>量化权重矩阵 × 向量: y[rows] = W[rows, cols] · x[cols]; weight 为行主序原始块数据。</summary>
    public static void Gemv(GgmlType t, ReadOnlySpan<byte> weight, int rows, int cols, ReadOnlySpan<float> x, Span<float> y)
        => GemvRange(t, weight, 0, rows, cols, x, y);

    /// <summary>
    /// 行区间 GEMV: 只算 <c>[rowStart, rowStart+rowCount)</c> 行 (多线程 driver 的基本块)。
    /// 每行点积互相独立 (无线程间归一化、无共享累加器) ⇒ 同一行无论在哪个区间、由哪条线程计算,
    /// **逐位相同** —— 这是「多线程结果 = 单线程结果」可机检的前提, 也是 <see cref="PartitionRows"/> 行分块成立的前提。
    /// </summary>
    public static void GemvRange(GgmlType t, ReadOnlySpan<byte> weight, int rowStart, int rowCount, int cols, ReadOnlySpan<float> x, Span<float> y)
    {
        if (rowStart < 0) throw new ArgumentOutOfRangeException(nameof(rowStart), $"gemv_row_start_negative: {rowStart}");
        if (rowCount < 0) throw new ArgumentOutOfRangeException(nameof(rowCount), $"gemv_row_count_negative: {rowCount}");
        if (x.Length < cols) throw new ArgumentException($"gemv_x_too_short: {x.Length} < {cols}");
        if (y.Length < rowStart + rowCount) throw new ArgumentException($"gemv_y_too_short: {y.Length} < {rowStart + rowCount}");
        switch (t)
        {
            case GgmlType.F32: GemvRawF32(weight, rowStart, rowCount, cols, x, y); return;
            case GgmlType.F16: GemvRawF16(weight, rowStart, rowCount, cols, x, y); return;
            default:
                GemvQuantized(t, weight, rowStart, rowCount, cols, x, y);
                return;
        }
    }

    /// <summary>
    /// 行分块: 每线程一个连续区间, **覆盖全部行且互不重叠** (sum(count)==rows, start 严格接续, 每区间 ≥1 行)。
    /// 线程数 &gt; 行数时收敛到行数。线程化与负控测试共用同一实现 ⇒ 不存在「产品一份、测试一份」的双口径。
    /// 行字节数**不在此处重算**, 一律取 <see cref="BlockLayout.RowBytes"/> (唯一来源)。
    /// </summary>
    public static (int Start, int Count)[] PartitionRows(int rows, int threads)
    {
        if (rows < 0) throw new ArgumentOutOfRangeException(nameof(rows), $"partition_rows_negative: {rows}");
        if (threads < 1) throw new ArgumentOutOfRangeException(nameof(threads), $"partition_threads_lt_1: {threads}");
        int parts = Math.Min(threads, Math.Max(rows, 1));
        var result = new (int Start, int Count)[parts];
        int baseRows = rows / parts, rem = rows % parts, start = 0;
        for (int i = 0; i < parts; i++)
        {
            int count = baseRows + (i < rem ? 1 : 0);
            result[i] = (start, count);
            start += count;
        }
        return result;
    }

    /// <summary>多线程 GEMV (常驻 byte[] 权重; 基准与测试入口): 结果与 <see cref="Gemv"/> **逐位相同**。</summary>
    public static void GemvParallel(GgmlType t, byte[] weight, int rows, int cols, float[] x, float[] y, int threads)
    {
        ArgumentNullException.ThrowIfNull(weight);
        unsafe
        {
            fixed (byte* wp = weight) GemvParallelPtr(t, wp, rows, cols, x, y, threads);
        }
    }

    /// <summary>
    /// 多线程 GEMV (mmap 零拷贝窗口直接给指针 ⇒ **不复制权重**)。线程只捕获指针 + 索引,
    /// span 在各线程体内构造 (span 不跨线程、不进闭包)。
    /// <paramref name="threads"/> ≤ 1 时走单线程路径 ⇒ 行为与改造前完全一致 (旧读数可作 A/B 基线)。
    /// </summary>
    public static unsafe void GemvParallelPtr(GgmlType t, byte* weight, int rows, int cols, float[] x, float[] y, int threads)
    {
        if (weight is null) throw new ArgumentNullException(nameof(weight));
        ArgumentNullException.ThrowIfNull(x);
        ArgumentNullException.ThrowIfNull(y);
        if (threads < 1) throw new ArgumentOutOfRangeException(nameof(threads), $"gemv_threads_lt_1: {threads}");
        if (rows < 0) throw new ArgumentOutOfRangeException(nameof(rows), $"gemv_rows_negative: {rows}");
        long rowBytes = BlockLayout.RowBytes(t, cols);
        if (threads == 1 || rows <= 1)
        {
            GemvRange(t, new ReadOnlySpan<byte>(weight, checked((int)(rowBytes * rows))), 0, rows, cols, x, y);
            return;
        }
        var parts = PartitionRows(rows, threads);
        var tasks = new Task[parts.Length];
        for (int i = 0; i < parts.Length; i++)
        {
            int start = parts[i].Start, count = parts[i].Count;
            tasks[i] = Task.Run(() =>
            {
                var w = new ReadOnlySpan<byte>(weight + (long)start * rowBytes, checked((int)((long)count * rowBytes)));
                GemvRange(t, w, 0, count, cols, x, new Span<float>(y, start, count));
            });
        }
        Task.WaitAll(tasks);
    }

    private static void GemvRawF32(ReadOnlySpan<byte> w, int rowStart, int rowCount, int cols, ReadOnlySpan<float> x, Span<float> y)
    {
        for (int r = 0; r < rowCount; r++)
        {
            var row = w.Slice((int)((long)(rowStart + r) * cols * 4), cols * 4);
            float sum = 0;
            for (int c = 0; c < cols; c++)
                sum += BitConverter.Int32BitsToSingle(row[c * 4] | (row[c * 4 + 1] << 8) | (row[c * 4 + 2] << 16) | (row[c * 4 + 3] << 24)) * x[c];
            y[rowStart + r] = sum;
        }
    }

    private static void GemvRawF16(ReadOnlySpan<byte> w, int rowStart, int rowCount, int cols, ReadOnlySpan<float> x, Span<float> y)
    {
        Span<float> tmp = cols <= 8192 ? stackalloc float[cols] : new float[cols];
        for (int r = 0; r < rowCount; r++)
        {
            Dequant.RowAt(GgmlType.F16, w, rowStart + r, cols, tmp);
            y[rowStart + r] = TensorPrimitives.Dot(tmp.Slice(0, cols), x.Slice(0, cols));
        }
    }

    /// <summary>块量化类型: 逐行 → 逐块反量化 → 点积融合 (不物化整行)</summary>
    private static void GemvQuantized(GgmlType t, ReadOnlySpan<byte> w, int rowStart, int rowCount, int cols, ReadOnlySpan<float> x, Span<float> y)
    {
        var (be, bb) = BlockLayout.Of(t);
        if (cols % be != 0) throw new NotSupportedException($"gemv_cols_not_block_aligned: cols={cols} block={be} type={t}");
        int blocks = cols / be;
        Span<float> blk = stackalloc float[256];
        if (be > 256) throw new NotSupportedException($"block_too_large: {be}");
        long rowBytes = (long)blocks * bb;

        for (int r = 0; r < rowCount; r++)
        {
            var row = w.Slice((int)((long)(rowStart + r) * rowBytes), (int)rowBytes);
            float sum = 0;
            for (int b = 0; b < blocks; b++)
            {
                var src = row.Slice(b * bb, bb);
                var dstSlice = blk.Slice(0, be);
                Dequant.Row(t, src, dstSlice, be);
                sum += TensorPrimitives.Dot(dstSlice, x.Slice(b * be, be));
            }
            y[rowStart + r] = sum;
        }
    }

    /// <summary>对照实现: 先物化整行再点积 (只用于 A/B 峰值内存对照, 不进热路径)</summary>
    public static void GemvMaterialized(GgmlType t, ReadOnlySpan<byte> weight, int rows, int cols, ReadOnlySpan<float> x, Span<float> y, Action<long>? onRowMaterialized = null)
    {
        var rowBuf = new float[cols];
        for (int r = 0; r < rows; r++)
        {
            Dequant.RowAt(t, weight, r, cols, rowBuf);
            y[r] = TensorPrimitives.Dot(rowBuf, x.Slice(0, cols));
            onRowMaterialized?.Invoke((long)cols * 4);
        }
    }

    public static void MatVecF32(ReadOnlySpan<float> w, int rows, int cols, ReadOnlySpan<float> x, Span<float> y)
    {
        for (int r = 0; r < rows; r++)
            y[r] = TensorPrimitives.Dot(w.Slice(r * cols, cols), x.Slice(0, cols));
    }

    /// <summary>RMSNorm: y = x / sqrt(mean(x^2)+eps) * weight</summary>
    public static void RmsNorm(ReadOnlySpan<float> x, ReadOnlySpan<float> weight, float eps, Span<float> y)
    {
        int n = x.Length;
        var tmp = new float[n];
        TensorPrimitives.Multiply(x, x, tmp);
        float ms = TensorPrimitives.Sum(tmp) / n;
        float scale = 1f / MathF.Sqrt(ms + eps);
        for (int i = 0; i < n; i++) y[i] = x[i] * scale * weight[i];
    }

    /// <summary>LayerNorm (BGE/XLM-R 类编码器用)</summary>
    public static void LayerNorm(ReadOnlySpan<float> x, ReadOnlySpan<float> weight, ReadOnlySpan<float> bias, float eps, Span<float> y)
    {
        int n = x.Length;
        float mean = TensorPrimitives.Sum(x) / n;
        var tmp = new float[n];
        for (int i = 0; i < n; i++) tmp[i] = x[i] - mean;
        float var = TensorPrimitives.SumOfSquares(tmp) / n;
        float scale = 1f / MathF.Sqrt(var + eps);
        for (int i = 0; i < n; i++) y[i] = (x[i] - mean) * scale * weight[i] + bias[i];
    }

    /// <summary>SwiGLU: y = silu(g) * u</summary>
    public static void SwiGlu(ReadOnlySpan<float> gate, ReadOnlySpan<float> up, Span<float> y)
    {
        for (int i = 0; i < gate.Length; i++)
        {
            float g = gate[i];
            y[i] = g / (1f + MathF.Exp(-g)) * up[i];
        }
    }

    public static void SoftmaxInPlace(Span<float> x, int n)
    {
        float max = float.NegativeInfinity;
        for (int i = 0; i < n; i++) if (x[i] > max) max = x[i];
        float sum = 0;
        for (int i = 0; i < n; i++) { float e = MathF.Exp(x[i] - max); x[i] = e; sum += e; }
        if (sum <= 0) return;
        float inv = 1f / sum;
        for (int i = 0; i < n; i++) x[i] *= inv;
    }

    /// <summary>
    /// RoPE 直接实现 (无预计算表; 支持 YaRN 缩放参数 freq_base/factor/beta_fast/beta_slow/n_ctx_train)。
    /// 配对约定由 <paramref name="pairing"/> 给定 —— 与 <see cref="RopeTable"/> 对账时两者必须传同一约定,
    /// 否则"两个实现一致"只是共享同一个误解 (见 RoverRopeTests 的负控)。
    /// </summary>
    public static void Rope(Span<float> q, int nHeads, int headDim, int pos, float freqBase, int nCtxTrain, float factor, float betaFast, float betaSlow, RopePairing pairing)
    {
        bool neox = pairing == RopePairing.NeoxHalf;
        for (int h = 0; h < nHeads; h++)
        {
            var v = q.Slice(h * headDim, headDim);
            for (int i = 0; i < headDim / 2; i++)
            {
                float invFreq = 1f / MathF.Pow(freqBase, 2f * i / headDim);
                if (factor > 1f)
                {
                    float wavelen = 2f * MathF.PI / invFreq;
                    float low = nCtxTrain / betaFast;
                    float high = nCtxTrain / betaSlow;
                    float ramp = wavelen < low ? 0f : (wavelen > high ? 1f : (nCtxTrain / wavelen - betaFast) / (betaSlow - betaFast));
                    invFreq = invFreq / factor * (1f - ramp) + invFreq * ramp;
                }
                float theta = pos * invFreq;
                float c = MathF.Cos(theta), s = MathF.Sin(theta);
                int a0 = neox ? i : 2 * i;                    // NEOX: (i, i+d/2)   NORM: (2i, 2i+1)
                int b0 = neox ? i + headDim / 2 : 2 * i + 1;
                float x0 = v[a0], x1 = v[b0];
                v[a0] = x0 * c - x1 * s;
                v[b0] = x0 * s + x1 * c;
            }
        }
    }

    /// <summary>单头注意力 (query 与 kv cache 前 n 个位置); 返回加权后的 value 累积到 out</summary>
    public static void AttentionHead(ReadOnlySpan<float> query, ReadOnlySpan<float> keys, ReadOnlySpan<float> values,
        int n, int headDim, float scale, Span<float> scores, Span<float> outv)
    {
        for (int t = 0; t < n; t++)
        {
            float dot = 0;
            var k = keys.Slice(t * headDim, headDim);
            for (int d = 0; d < headDim; d++) dot += query[d] * k[d];
            scores[t] = dot * scale;
        }
        SoftmaxInPlace(scores, n);
        for (int d = 0; d < headDim; d++) outv[d] = 0;
        for (int t = 0; t < n; t++)
        {
            float w = scores[t];
            var v = values.Slice(t * headDim, headDim);
            for (int d = 0; d < headDim; d++) outv[d] += w * v[d];
        }
    }

    public static void AddInPlace(Span<float> a, ReadOnlySpan<float> b)
    {
        for (int i = 0; i < a.Length; i++) a[i] += b[i];
    }
}
