using System.Numerics;

namespace agent.rover.quant;

using agent.rover.gguf;

/// <summary>
/// 反量化内核 (C4): 逐字节对齐 ggml 参考实现 (本机 llama.cpp 源 ggml/src/ggml-quants.c)。
/// 每条内核都有一一对应的参考函数名 (见注释), 并由 /tmp 参考 .so 做逐元素对账 (dequant-check)。
/// 只用 <see cref="BitConverter.UInt16BitsToHalf"/> + 位运算 → AOT 安全, 无反射, 无平台分支。
/// </summary>
public static class Dequant
{
    public const int QK_K = 256;

    /// <summary>参考: dequantize_row_q4_K (ggml-quants.c:1529)</summary>
    public static void RowQ4K(ReadOnlySpan<byte> src, Span<float> dst, int elems)
    {
        if (elems % QK_K != 0) throw new ArgumentException($"q4k_not_block_aligned: {elems}");
        int nb = elems / QK_K;
        const int BlockBytes = 144;
        if (src.Length < (long)nb * BlockBytes) throw new ArgumentException($"q4k_src_too_short: {src.Length} < {(long)nb * BlockBytes}");

        int o = 0, so = 0;
        for (int i = 0; i < nb; i++)
        {
            ReadOnlySpan<byte> b = src.Slice(i * BlockBytes, BlockBytes);
            float d = F16(b, 0);
            float dmin = F16(b, 2);
            ReadOnlySpan<byte> scales = b.Slice(4, 12);
            ReadOnlySpan<byte> qs = b.Slice(16, 128);

            int is_ = 0, qi = 0;
            for (int j = 0; j < QK_K; j += 64)
            {
                GetScaleMinK4(is_ + 0, scales, out byte sc1, out byte m1);
                GetScaleMinK4(is_ + 1, scales, out byte sc2, out byte m2);
                float d1 = d * sc1, mm1 = dmin * m1;
                float d2 = d * sc2, mm2 = dmin * m2;
                for (int l = 0; l < 32; l++) dst[so + j + l] = d1 * (qs[qi + l] & 0xF) - mm1;
                for (int l = 0; l < 32; l++) dst[so + j + 32 + l] = d2 * (qs[qi + l] >> 4) - mm2;
                qi += 32;
                is_ += 2;
            }
            so += QK_K;
            o++;
        }
        _ = o;
    }

    /// <summary>参考: get_scale_min_k4 (ggml-quants.c:880)</summary>
    public static void GetScaleMinK4(int j, ReadOnlySpan<byte> q, out byte d, out byte m)
    {
        if (j < 4)
        {
            d = (byte)(q[j] & 63);
            m = (byte)(q[j + 4] & 63);
        }
        else
        {
            d = (byte)((q[j + 4] & 0xF) | ((q[j - 4] >> 6) << 4));
            m = (byte)((q[j + 4] >> 4) | ((q[j] >> 6) << 4));
        }
    }

    /// <summary>参考: dequantize_row_q6_K (ggml-quants.c:1939)</summary>
    public static void RowQ6K(ReadOnlySpan<byte> src, Span<float> dst, int elems)
    {
        if (elems % QK_K != 0) throw new ArgumentException($"q6k_not_block_aligned: {elems}");
        int nb = elems / QK_K;
        const int BlockBytes = 210;
        int so = 0;
        for (int i = 0; i < nb; i++)
        {
            ReadOnlySpan<byte> b = src.Slice(i * BlockBytes, BlockBytes);
            ReadOnlySpan<byte> ql = b.Slice(0, 128);
            ReadOnlySpan<byte> qh = b.Slice(128, 64);
            ReadOnlySpan<byte> sc = b.Slice(192, 16);
            float d = F16(b, 208);

            int qlo = 0, qho = 0, sco = 0;
            for (int n = 0; n < QK_K; n += 128)
            {
                for (int l = 0; l < 32; l++)
                {
                    int is_ = l / 16;
                    int q1 = ((ql[qlo + l] & 0xF) | (((qh[qho + l] >> 0) & 3) << 4)) - 32;
                    int q2 = ((ql[qlo + l + 32] & 0xF) | (((qh[qho + l] >> 2) & 3) << 4)) - 32;
                    int q3 = ((ql[qlo + l] >> 4) | (((qh[qho + l] >> 4) & 3) << 4)) - 32;
                    int q4 = ((ql[qlo + l + 32] >> 4) | (((qh[qho + l] >> 6) & 3) << 4)) - 32;
                    dst[so + n + l + 0] = d * (sbyte)sc[sco + is_ + 0] * q1;
                    dst[so + n + l + 32] = d * (sbyte)sc[sco + is_ + 2] * q2;
                    dst[so + n + l + 64] = d * (sbyte)sc[sco + is_ + 4] * q3;
                    dst[so + n + l + 96] = d * (sbyte)sc[sco + is_ + 6] * q4;
                }
                qlo += 64;
                qho += 32;
                sco += 8;
            }
            so += QK_K;
        }
    }

    /// <summary>参考: dequantize_row_q8_0 (ggml-quants.c:553)</summary>
    public static void RowQ8_0(ReadOnlySpan<byte> src, Span<float> dst, int elems)
    {
        const int BlockElems = 32, BlockBytes = 34;
        int nb = elems / BlockElems;
        for (int i = 0; i < nb; i++)
        {
            ReadOnlySpan<byte> b = src.Slice(i * BlockBytes, BlockBytes);
            float d = F16(b, 0);
            for (int j = 0; j < 32; j++) dst[i * 32 + j] = d * (sbyte)b[2 + j];
        }
    }

    /// <summary>参考: dequantize_row_q4_0 (ggml-quants.c:459)</summary>
    public static void RowQ4_0(ReadOnlySpan<byte> src, Span<float> dst, int elems)
    {
        const int BlockElems = 32, BlockBytes = 18;
        int nb = elems / BlockElems;
        for (int i = 0; i < nb; i++)
        {
            ReadOnlySpan<byte> b = src.Slice(i * BlockBytes, BlockBytes);
            float d = F16(b, 0);
            for (int j = 0; j < 16; j++)
            {
                int lo = (b[2 + j] & 0xF) - 8;
                int hi = (b[2 + j] >> 4) - 8;
                dst[i * 32 + j] = d * lo;
                dst[i * 32 + 16 + j] = d * hi;
            }
        }
    }

    public static void RowF16(ReadOnlySpan<byte> src, Span<float> dst, int elems)
    {
        for (int i = 0; i < elems; i++) dst[i] = F16(src, i * 2);
    }

    public static void RowBF16(ReadOnlySpan<byte> src, Span<float> dst, int elems)
    {
        for (int i = 0; i < elems; i++)
        {
            uint bits = (uint)(src[i * 2] | (src[i * 2 + 1] << 8)) << 16;
            dst[i] = BitConverter.UInt32BitsToSingle(bits);
        }
    }

    public static void RowF32(ReadOnlySpan<byte> src, Span<float> dst, int elems)
    {
        for (int i = 0; i < elems; i++) dst[i] = BitConverter.Int32BitsToSingle(src[i * 4] | (src[i * 4 + 1] << 8) | (src[i * 4 + 2] << 16) | (src[i * 4 + 3] << 24));
    }

    /// <summary>类型分派 (只接受已实现类型; 其余抛, 不静默当 F32)</summary>
    public static void Row(GgmlType t, ReadOnlySpan<byte> src, Span<float> dst, int elems)
    {
        switch (t)
        {
            case GgmlType.F32: RowF32(src, dst, elems); break;
            case GgmlType.F16: RowF16(src, dst, elems); break;
            case GgmlType.BF16: RowBF16(src, dst, elems); break;
            case GgmlType.Q4_0: RowQ4_0(src, dst, elems); break;
            case GgmlType.Q8_0: RowQ8_0(src, dst, elems); break;
            case GgmlType.Q4_K: RowQ4K(src, dst, elems); break;
            case GgmlType.Q6_K: RowQ6K(src, dst, elems); break;
            default: throw new NotSupportedException($"dequant_not_implemented: {t}");
        }
    }

    /// <summary>把 src 的某一行 (行内元素数 rowElems) 反量化到 dst (长度 ≥ rowElems)</summary>
    public static void RowAt(GgmlType t, ReadOnlySpan<byte> tensor, long rowIndex, int rowElems, Span<float> dst)
    {
        long rowBytes = BlockLayout.RowBytes(t, rowElems);
        long off = rowIndex * rowBytes;
        if (off + rowBytes > tensor.Length) throw new ArgumentOutOfRangeException(nameof(rowIndex), $"row_out_of_range: {rowIndex}");
        Row(t, tensor.Slice((int)off, (int)rowBytes), dst, rowElems);
    }

    internal static float F16(ReadOnlySpan<byte> b, int off)
    {
        ushort u = (ushort)(b[off] | (b[off + 1] << 8));
        return (float)BitConverter.UInt16BitsToHalf(u);
    }
}
