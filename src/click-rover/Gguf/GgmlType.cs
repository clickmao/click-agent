namespace clickrover.gguf;

/// <summary>
/// ggml 张量量化类型 (与 ggml.h 的 enum ggml_type 数值一致 — 这是 GGUF 文件里的 u32 值)。
/// 只列本引擎会遇到的类型; 未实现反量化的类型在解析期即明确报错 (不静默当 F32)。
/// </summary>
public enum GgmlType : uint
{
    F32 = 0,
    F16 = 1,
    Q4_0 = 2,
    Q4_1 = 3,
    Q5_0 = 6,
    Q5_1 = 7,
    Q8_0 = 8,
    Q8_1 = 9,
    Q2_K = 10,
    Q3_K = 11,
    Q4_K = 12,
    Q5_K = 13,
    Q6_K = 14,
    Q8_K = 15,
    IQ4_NL = 20,
    BF16 = 30,
}

/// <summary>
/// 块布局表: 每块元素数 + 每块字节数 (逐字对齐 ggml-common.h 的 struct 尺寸)。
/// 行字节数 = 行元素数 / ElementsPerBlock * BytesPerBlock (与 ggml_row_size 同义)。
/// </summary>
public static class BlockLayout
{
    /// <summary>返回 (每块元素数, 每块字节数); 未知类型 → 抛 (不猜)。</summary>
    public static (int Elems, int Bytes) Of(GgmlType t) => t switch
    {
        GgmlType.F32 => (1, 4),
        GgmlType.F16 => (1, 2),
        GgmlType.BF16 => (1, 2),
        GgmlType.Q4_0 => (32, 18),   // d(2) + qs(16)
        GgmlType.Q4_1 => (32, 20),   // d(2)+m(2) + qs(16)
        GgmlType.Q5_0 => (32, 22),   // d(2)+qh(4) + qs(16)
        GgmlType.Q5_1 => (32, 24),   // d(2)+m(2)+qh(4) + qs(16)
        GgmlType.Q8_0 => (32, 34),   // d(2) + qs(32)
        GgmlType.Q8_1 => (32, 40),   // d(4)+s(4) + qs(32)
        GgmlType.Q2_K => (256, 84),  // scales(16)+qs(64)+d(2)+dmin(2)
        GgmlType.Q3_K => (256, 110), // hmask(32)+qs(64)+scales(12)+d(2)
        GgmlType.Q4_K => (256, 144), // d(2)+dmin(2)+scales(12)+qs(128)
        GgmlType.Q5_K => (256, 176), // d(2)+dmin(2)+scales(12)+qs(128)+qh(32)
        GgmlType.Q6_K => (256, 210), // ql(128)+qh(64)+scales(16)+d(2)
        GgmlType.Q8_K => (256, 292), // d(4)+qs(256)+bsums(32)
        GgmlType.IQ4_NL => (32, 18), // d(2) + qs(16)
        _ => throw new NotSupportedException($"tensor_type_unsupported: ggml type {(uint)t} ({t})"),
    };

    /// <summary>可反量化的类型 (其余会在加载期拒绝, 不静默降级)。</summary>
    public static bool IsDequantizable(GgmlType t) => t switch
    {
        GgmlType.F32 or GgmlType.F16 or GgmlType.BF16 => true,
        GgmlType.Q4_0 or GgmlType.Q8_0 or GgmlType.Q4_K or GgmlType.Q6_K => true,
        _ => false,
    };

    public static string Name(GgmlType t) => t.ToString();

    public static long RowBytes(GgmlType t, long rowElems)
    {
        var (elems, bytes) = Of(t);
        if (rowElems % elems != 0)
            throw new InvalidOperationException($"row_not_block_aligned: {rowElems} % {elems} != 0 (type {t})");
        return rowElems / elems * bytes;
    }

    public static long TensorBytes(GgmlType t, ReadOnlySpan<long> dims)
    {
        long elems = 1;
        foreach (var d in dims) elems *= d;
        var (e, b) = Of(t);
        if (elems % e != 0)
            throw new InvalidOperationException($"tensor_not_block_aligned: {elems} % {e} != 0 (type {t})");
        return elems / e * b;
    }
}
