using Xunit;
using agent.rover.gguf;
using agent.rover.runtime;

namespace agent.tests;

/// <summary>
/// R402 步 2 · 多线程 GEMV (=「计算直测」所依赖的内核能力) 测试。
/// 断言绑定真实行为, 每条都配反向控制:
///  ① 正确性: 合成 Q8_0 (d=1.0 ⇒ 反量化恒等于 int8) 的 GEMV 结果 vs 测试内**独立算法**算出的期望值;
///  ② 区间性: 行区间 GEMV 拼接 == 整块 GEMV (逐位);
///  ③ 不变性: 1 vs N 线程**逐位相同** (多线程只改"谁算哪些行", 不改任何行的算式);
///  ④ 分块性: PartitionRows 覆盖全部行/连续/无重叠, 且**留缝或重叠的坏分块必须被判红** (否则 ②③ 无判别力);
///  ⑤ 边界: 线程数 > 行数收敛、threads<1 抛、rows=0/1 不崩。
/// </summary>
public class RoverComputeKernelTests
{
    // ---------- 合成张量: Q8_0 每块 = d(2B fp16) + 32×int8; d=1.0 ⇒ 反量化恒等于 int8 值 ⇒ 期望值可独立算 ----------
    private static byte[] Q8_0Tensor(int rows, int cols, out sbyte[,] quant)
    {
        Assert.Equal(0, cols % 32);
        int blocks = cols / 32;
        var bytes = new byte[rows * blocks * 34];
        quant = new sbyte[rows, cols];
        for (int r = 0; r < rows; r++)
            for (int b = 0; b < blocks; b++)
            {
                int off = ((r * blocks) + b) * 34;
                bytes[off] = 0x00; bytes[off + 1] = 0x3C;            // fp16 = 1.0
                for (int j = 0; j < 32; j++)
                {
                    sbyte v = (sbyte)(((r * 131 + b * 17 + j * 7) % 255) - 127);
                    quant[r, b * 32 + j] = v;
                    bytes[off + 2 + j] = unchecked((byte)v);
                }
            }
        return bytes;
    }

    private static float[] MakeX(int cols, int seed)
    {
        var x = new float[cols];
        for (int i = 0; i < cols; i++)
            x[i] = (float)(Math.Sin((i + seed) * 0.001953125) * 0.5 + Math.Cos((i * 3 + seed) * 0.0009765625) * 0.25);
        return x;
    }

    private static ulong Bits(float f) => unchecked((uint)BitConverter.SingleToInt32Bits(f));
    private static void AssertBitwiseEqual(float[] a, float[] b)
    {
        Assert.Equal(a.Length, b.Length);
        for (int i = 0; i < a.Length; i++)
            Assert.True(Bits(a[i]) == Bits(b[i]), $"第 {i} 项非逐位相同: {(a[i] == b[i] ? "值同但位不同" : "值不同")} a={a[i]:R} b={b[i]:R}");
    }

    [Fact]
    public void Q8_0_Gemv_MatchesIndependentOracle_And_IsSensitiveToInput()
    {
        const int rows = 8, cols = 64;
        var w = Q8_0Tensor(rows, cols, out var q);
        var x = MakeX(cols, 12345);
        var y = new float[rows];
        CpuKernels.Gemv(GgmlType.Q8_0, w, rows, cols, x, y);

        // 独立期望 (double 累加, 与内核的块内 TensorPrimitives.Dot 不同实现/不同顺序)
        for (int r = 0; r < rows; r++)
        {
            double e = 0;
            for (int c = 0; c < cols; c++) e += q[r, c] * (double)x[c];
            Assert.True(Math.Abs(e - y[r]) <= 1e-3 * Math.Max(1.0, Math.Abs(e)), $"行 {r}: 期望 {e} 实得 {y[r]}");
        }

        // 反向控制: 换一条输入 ⇒ 结果必须变 (否则断言可能恒真)
        var x2 = MakeX(cols, 999);
        var y2 = new float[rows];
        CpuKernels.Gemv(GgmlType.Q8_0, w, rows, cols, x2, y2);
        Assert.False(y.SequenceEqual(y2), "换输入后结果不变 ⇒ 该测试无判别力");

        // 反向控制: 换权重块 (改一个 int8) ⇒ 结果必须变
        var w2 = (byte[])w.Clone();
        w2[2] = unchecked((byte)(sbyte)(w2[2] + 1));
        var y3 = new float[rows];
        CpuKernels.Gemv(GgmlType.Q8_0, w2, rows, cols, x, y3);
        Assert.False(y.SequenceEqual(y3), "改权重后结果不变 ⇒ 该测试无判别力");
    }

    [Fact]
    public void GemvRange_PartitionedRows_MatchWholeGemv_Bitwise()
    {
        const int rows = 8, cols = 64;
        var w = Q8_0Tensor(rows, cols, out _);
        var x = MakeX(cols, 7);
        var whole = new float[rows];
        CpuKernels.Gemv(GgmlType.Q8_0, w, rows, cols, x, whole);

        var parts = CpuKernels.PartitionRows(rows, 3);
        Assert.Equal(3, parts.Length);
        var spliced = new float[rows];
        foreach (var (start, count) in parts)
            CpuKernels.GemvRange(GgmlType.Q8_0, w, start, count, cols, x, spliced);

        AssertBitwiseEqual(whole, spliced);
    }

    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(8)]
    [InlineData(64)]
    public void GemvParallel_BitwiseIdenticalToSerial(int threads)
    {
        const int rows = 8, cols = 128;
        var w = Q8_0Tensor(rows, cols, out _);
        var x = MakeX(cols, 4242);
        var serial = new float[rows];
        CpuKernels.Gemv(GgmlType.Q8_0, w, rows, cols, x, serial);
        var parallel = new float[rows];
        CpuKernels.GemvParallel(GgmlType.Q8_0, w, rows, cols, x, parallel, threads);
        AssertBitwiseEqual(serial, parallel);
    }

    [Fact]
    public void GemvParallel_BitwiseIdentical_OnIrregularRows_AndThreadClamp()
    {
        // 29 行 / 64 列: 行数不是线程数整数倍 ⇒ 分块长度不均, 仍须逐位相同
        const int rows = 29, cols = 64;
        var w = Q8_0Tensor(rows, cols, out _);
        var x = MakeX(cols, 31);
        var serial = new float[rows];
        CpuKernels.Gemv(GgmlType.Q8_0, w, rows, cols, x, serial);
        foreach (int threads in new[] { 2, 3, 4, 5, 7, 29, 4096 })
        {
            var got = new float[rows];
            CpuKernels.GemvParallel(GgmlType.Q8_0, w, rows, cols, x, got, threads);
            AssertBitwiseEqual(serial, got);
        }
    }

    // ---------- 分块不变量 + 反向控制 (留缝/重叠的坏分块必须被判红) ----------
    private static bool CoversAllRows((int Start, int Count)[] parts, int rows)
    {
        // 口径: 区间必须**恰好**覆盖 [0, rows) —— start 严格接续, 每区间 ≥1 行;
        // 唯一例外是 rows==0 (空任务) 时允许出现一个空块, 这不算"留缝"。
        if (rows == 0) return parts.Length == 1 && parts[0] == (0, 0);
        int expect = 0;
        foreach (var (start, count) in parts)
        {
            if (start != expect) return false;
            if (count < 1) return false;
            expect += count;
        }
        return expect == rows;
    }

    [Fact]
    public void PartitionRows_CoversAllRows_And_BadPartitionsAreRejected()
    {
        var cases = new (int Rows, int Threads)[] { (0, 1), (0, 4), (1, 1), (1, 8), (8, 1), (8, 3), (8, 8), (9, 4), (100, 7), (64, 2) };
        foreach (var (rows, threads) in cases)
        {
            var parts = CpuKernels.PartitionRows(rows, threads);
            Assert.True(CoversAllRows(parts, rows), $"rows={rows} threads={threads} 的分块未覆盖全部行");
            Assert.True(parts.Length <= Math.Max(rows, 1), $"rows={rows} threads={threads} 分块数超过行数");
        }
        Assert.Single(CpuKernels.PartitionRows(8, 1));
        Assert.Equal(8, CpuKernels.PartitionRows(8, 4096).Length);

        // 反向控制 1: 丢掉最后一块 (留缝) ⇒ 必须判红
        var gap = CpuKernels.PartitionRows(9, 4).Take(3).ToArray();
        Assert.False(CoversAllRows(gap, 9), "留缝的坏分块未被判红 ⇒ 分块不变量无判别力");
        // 反向控制 2: 某块多吃一行 (重叠 + 后块错位) ⇒ 必须判红
        var overlap = (CpuKernels.PartitionRows(9, 4));
        overlap[0] = (overlap[0].Start, overlap[0].Count + 1);
        Assert.False(CoversAllRows(overlap, 9), "重叠的坏分块未被判红 ⇒ 分块不变量无判别力");
        // 反向控制 3: 空区间 ⇒ 必须判红
        var empty = (CpuKernels.PartitionRows(4, 2));
        empty[1] = (empty[1].Start, 0);
        Assert.False(CoversAllRows(empty, 4), "空区间的坏分块未被判红");
        // 反向控制 4: rows=0 的空块在非空任务里必须判红 (口径例外只对空任务生效)
        Assert.False(CoversAllRows(CpuKernels.PartitionRows(0, 1), 1), "空任务分块被误当成非空任务的合法分块");
    }

    [Fact]
    public void GemvParallel_GapInCoverage_LeavesRowsUnwritten_SoDefectIsDetectable()
    {
        const int rows = 9, cols = 64;
        var w = Q8_0Tensor(rows, cols, out _);
        var x = MakeX(cols, 5);
        var full = new float[rows];
        CpuKernels.Gemv(GgmlType.Q8_0, w, rows, cols, x, full);

        // 模拟"线程分块留缝"缺陷: 只跑前 3 块 ⇒ 末块覆盖的行保持哨兵 NaN
        var y = new float[rows];
        Array.Fill(y, float.NaN);
        foreach (var (start, count) in CpuKernels.PartitionRows(rows, 4).Take(3))
            CpuKernels.GemvRange(GgmlType.Q8_0, w, start, count, cols, x, y);
        int nanCount = y.Count(float.IsNaN);
        Assert.True(nanCount > 0, "留缝分块竟然没留下未写行 ⇒ 「逐位相同」断言对该缺陷无判别力");
        Assert.False(Bits(y[rows - 1]) == Bits(full[rows - 1]), "未写行的值碰巧等于正确值 ⇒ 缺陷会被漏检");
    }

    [Fact]
    public void GemvParallel_RejectsNonPositiveThreads()
    {
        var w = Q8_0Tensor(2, 32, out _);
        var x = MakeX(32, 1);
        var y = new float[2];
        Assert.Throws<ArgumentOutOfRangeException>(() => CpuKernels.GemvParallel(GgmlType.Q8_0, w, 2, 32, x, y, 0));
        Assert.Throws<ArgumentOutOfRangeException>(() => CpuKernels.GemvParallel(GgmlType.Q8_0, w, 2, 32, x, y, -3));
        Assert.Throws<ArgumentOutOfRangeException>(() => CpuKernels.PartitionRows(2, 0));
        Assert.Throws<ArgumentOutOfRangeException>(() => CpuKernels.PartitionRows(-1, 2));
        Assert.Throws<ArgumentException>(() => CpuKernels.GemvRange(GgmlType.Q8_0, w, 0, 2, 64, x, y));  // x 太短
        Assert.Throws<ArgumentException>(() => CpuKernels.GemvRange(GgmlType.Q8_0, w, 1, 2, 32, x, y));  // y 太短
    }

    [Fact]
    public void RowBytes_MatchesSynthesizedByteSize()
    {
        var q8 = Q8_0Tensor(4, 64, out _);
        Assert.Equal(4 * BlockLayout.RowBytes(GgmlType.Q8_0, 64), q8.Length);
        Assert.Equal(64 * 4L, BlockLayout.RowBytes(GgmlType.F32, 64));
        Assert.Equal(64 * 2L, BlockLayout.RowBytes(GgmlType.F16, 64));
    }

    [Fact]
    public void RowBytes_NotBlockAligned_Throws_InsteadOfSilentlyRounding()
    {
        Assert.Throws<InvalidOperationException>(() => BlockLayout.RowBytes(GgmlType.Q8_0, 48));   // 48 % 32 != 0
        Assert.Throws<NotSupportedException>(() => BlockLayout.Of((GgmlType)9999));               // 未知类型不静默当 F32
    }
}
