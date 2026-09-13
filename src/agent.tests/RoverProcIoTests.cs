using Xunit;
using agent.rover.runtime;

namespace agent.tests;

/// <summary>
/// R402 · 归因读数 (进程 I/O / 缺页) 的**解析与口径**测试。
///
/// 为什么这类测试值钱: 解析失败的形态是**静默 0** —— 计数器读成 0 时, 报告会显示
/// 「盘读 0 字节 ⇒ 瓶颈在计算」这种**方向相反的结论**, 而且不报错。所以:
///  ① 字段偏移用带括号/空格 comm 的真实 /proc 形态钉死 (off-by-one 必红);
///  ② 缺字段 ⇒ Available=false 且值为 0 (诚实不可测, 不是「测得 0」);
///  ③ 每 pass 分母固定为 **pass 数** (含 prefill) —— R400 台账曾把含 prefill 的分子除以 decode 步数,
///     报出 22.2 GB/token (「5.3× 模型体积」) 而同一报告边界又写 ≈1× ⇒ 口径缺陷, 用测试钉住。
/// </summary>
public class RoverProcIoTests
{
    private const string IoText =
        "rchar: 1234567\n" +
        "wchar: 42\n" +
        "syscr: 987\n" +
        "syscw: 3\n" +
        "read_bytes: 4096000\n" +
        "write_bytes: 0\n";

    // 真实 /proc/self/stat 字段序 (comm 之后): state(3) ppid(4) pgrp(5) session(6) tty_nr(7)
    // tpgid(8) flags(9) **minflt(10)** cminflt(11) **majflt(12)** ... ⇒ 切点后 idx7=minflt, idx9=majflt。
    // comm 含空格与括号 ⇒ 只能从最后一个 ')' 之后切 (真实形态)。
    private const string StatText =
        "1234 (agent rover (net10.0)) S 1 1234 1234 0 -1 4194560 915 77 1002 0 0 20 0 1 0 0 0 0 0 0 0 0 0 0 0\n";

    [Fact]
    public void Parse_ReadsDiskAndSyscallCounters()
    {
        var s = ProcIoSnapshot.Parse(IoText, StatText);
        Assert.True(s.Available);
        Assert.Equal(4096000, s.ReadBytes);     // 真正提交块设备的字节
        Assert.Equal(1234567, s.RcharBytes);    // 走 syscall 的字节 (含页缓存命中)
        Assert.Equal(987, s.Syscr);
        Assert.Equal(915, s.MinFlt);
        Assert.Equal(1002, s.MajFlt);
    }

    [Fact]
    public void Parse_CommWithSpacesAndParens_DoesNotShiftFaultFields()
    {
        // 负控: 若按**第一个** ')' 或按整行 split 解析, minflt/majflt 会取到别的字段 (此处必红)
        var shifted = ProcIoSnapshot.Parse(IoText,
            "1234 (x) S 1 2 3 4 5 6 12 13 14 15 16 17 18 19 20 21\n");
        Assert.True(shifted.Available);
        Assert.Equal(12, shifted.MinFlt);   // 字段 10 (idx 7) = 12
        Assert.Equal(14, shifted.MajFlt);   // 字段 12 (idx 9) = 14
    }

    [Fact]
    public void Parse_MissingOrMalformedFields_ReportsUnavailableNotZero()
    {
        Assert.False(ProcIoSnapshot.Parse("", "").Available);
        Assert.False(ProcIoSnapshot.Parse(IoText, "").Available);           // 无 stat ⇒ 缺页口径不可用
        Assert.False(ProcIoSnapshot.Parse("nothing: here\n", StatText).Available);
        Assert.False(ProcIoSnapshot.Parse("read_bytes: not_a_number\n", StatText).Available);   // 不抛异常, 也不假装 0 可用
        var shortStat = ProcIoSnapshot.Parse(IoText, "1 (x) S 1 2 3 4 5\n");
        Assert.False(shortStat.Available);
    }

    [Fact]
    public void Delta_SubtractsPerField_AndPropagatesUnavailability()
    {
        var a = ProcIoSnapshot.Parse(IoText, StatText);
        var b = ProcIoSnapshot.Parse(
            "rchar: 2234567\nsyscr: 1987\nread_bytes: 8192000\n",
            "1234 (x) S 1 2 3 4 5 6 1915 8 2002 10 11 12 13 14 15 16 17 18 19 20\n");
        var d = ProcIoSnapshot.Delta(a, b);
        Assert.True(d.Available);
        Assert.Equal(4096000, d.ReadBytes);
        Assert.Equal(1000000, d.RcharBytes);
        Assert.Equal(1000, d.Syscr);
        Assert.Equal(1000, d.MinFlt);
        Assert.Equal(1000, d.MajFlt);

        var u = ProcIoSnapshot.Delta(ProcIoSnapshot.Unavailable, b);
        Assert.False(u.Available);      // 一侧不可用 ⇒ 差值不可用 (不把未知当 0)
    }

    /// <summary>口径钉死: 每 pass 的分母 = pass 数 (prefill + decode 全算), 不是 decode 步数。</summary>
    [Fact]
    public void IoThroughput_PerPassDenominator_IsPassCountNotDecodeSteps()
    {
        const long modelBytes = 4_223_362_304;
        long streamed = 45 * modelBytes;                 // 37 prefill + 8 decode, 每 pass 扫一遍全权重
        Assert.Equal((double)modelBytes, IoThroughput.PerPass(streamed, 45), 0);
        Assert.Equal(1.0, IoThroughput.Ratio(streamed, streamed), 3);      // 全漏页缓存 ⇒ 比值 1
        Assert.Equal(0.25, IoThroughput.Ratio(modelBytes, 4 * modelBytes), 3);
        // 反向负控: 分母误取 decode 步数 (8) ⇒ 45/8 × 模型体积 ≈ 23.8 GB/pass (≈5.6× 模型体积)。
        // R400 台账的「22.2 GB/token」是同源口径错值 (分子含 prefill, 分母只数 decode), 修正表见报告 §3。
        Assert.InRange(IoThroughput.PerPass(streamed, 8), 23.7e9, 23.8e9);
    }

    [Fact]
    public void IoThroughput_ZeroDenominator_ReturnsZeroNotNaN()
    {
        Assert.Equal(0d, IoThroughput.PerPass(100, 0));
        Assert.Equal(0d, IoThroughput.Ratio(100, 0));
        Assert.False(double.IsNaN(IoThroughput.PerPass(100, 0)));   // NaN 会污染聚合均值
    }
}
