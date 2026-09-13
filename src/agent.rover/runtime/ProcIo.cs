namespace agent.rover.runtime;

/// <summary>
/// 进程级 I/O 与缺页读数 (<c>/proc/self/io</c> + <c>/proc/self/stat</c>)。
///
/// 存在理由 (R402 度量子步骤): 本机 2 vCPU / 3.57 GiB 物理内存而模型 3.93 GiB ⇒ 权重页
/// **原理上无法整份驻留** ⇒ 「每 token 25.7 s」到底是**盘读等待**还是**反量化计算**必须用数据分开,
/// 否则优化靶点 (mmap 策略 vs 批 prefill vs 线程 vs SIMD) 只能靠猜。
///
/// 语义纪律:
///  · <c>ReadBytes</c> 只计**真正提交到块设备**的字节 (页缓存命中不计) —— 这是判定「页缓存是否吃得下模型」的唯一硬指标;
///  · <c>RcharBytes</c> 是走 syscall 的字节 (含页缓存命中);
///  · <c>MajFlt</c> = 需要磁盘 I/O 的缺页次数 (与盘读正相关); <c>MinFlt</c> = 页缓存内解决;
///  · 读不到 (非 Linux / 无权限) 一律返回 0 并留 <see cref="Available"/>=false, **不编造**。
/// </summary>
public readonly record struct ProcIoSnapshot(
    long ReadBytes, long RcharBytes, long Syscr, long MinFlt, long MajFlt, bool Available)
{
    public static readonly ProcIoSnapshot Unavailable = new(0, 0, 0, 0, 0, false);

    /// <summary>逐字段求差 (快照语义: 都是单调计数器); 任一侧不可用 ⇒ 结果不可用。</summary>
    public static ProcIoSnapshot Delta(ProcIoSnapshot before, ProcIoSnapshot after) =>
        new(after.ReadBytes - before.ReadBytes,
            after.RcharBytes - before.RcharBytes,
            after.Syscr - before.Syscr,
            after.MinFlt - before.MinFlt,
            after.MajFlt - before.MajFlt,
            before.Available && after.Available);

    public static ProcIoSnapshot Capture()
    {
        try
        {
            if (!File.Exists("/proc/self/io")) return Unavailable;
            string io = File.ReadAllText("/proc/self/io");
            string stat = File.Exists("/proc/self/stat") ? File.ReadAllText("/proc/self/stat") : "";
            return Parse(io, stat);
        }
        catch (IOException) { return Unavailable; }
        catch (UnauthorizedAccessException) { return Unavailable; }
    }

    /// <summary>纯函数形态 (便于离线用夹具文本回归): 解析 /proc/self/io 与 /proc/self/stat 原文。</summary>
    public static ProcIoSnapshot Parse(string ioText, string statText)
    {
        long readBytes = 0, rchar = 0, syscr = 0, minFlt = 0, majFlt = 0;
        bool anyIo = false;
        foreach (var raw in ioText.Split('\n'))
        {
            int c = raw.IndexOf(':');
            if (c <= 0) continue;
            string key = raw[..c].Trim();
            string val = raw[(c + 1)..].Trim();
            if (!long.TryParse(val, out long n)) continue;
            switch (key)
            {
                case "read_bytes": readBytes = n; anyIo = true; break;
                case "rchar": rchar = n; anyIo = true; break;
                case "syscr": syscr = n; anyIo = true; break;
            }
        }
        // /proc/self/stat: comm (字段 2) 可能含空格/括号 ⇒ 只能从**最后一个 ')'** 之后切,
        // 之后第 0 个 token 是 state(字段 3), 故 minflt(字段 10)=idx 7, majflt(字段 12)=idx 9。
        int rp = statText.LastIndexOf(')');
        bool anyStat = false;
        if (rp >= 0)
        {
            var f = statText[(rp + 1)..].Split(' ', StringSplitOptions.RemoveEmptyEntries);
            if (f.Length > 9 &&
                long.TryParse(f[7], out long mn) && long.TryParse(f[9], out long mj))
            {
                minFlt = mn; majFlt = mj; anyStat = true;
            }
        }
        return new ProcIoSnapshot(readBytes, rchar, syscr, minFlt, majFlt, anyIo && anyStat);
    }
}

/// <summary>
/// 吞吐/比值口径的**单一来源** (放这里是因为它被共享给测试工程, 而 ForwardPass 不共享)。
///
/// R400 台账缺陷的口径根因: 「流式字节数」的分子含 prefill 的全部 pass, 分母却只取 decode 步数
/// ⇒ 报出 22.2 GB/token (「5.3× 模型体积」) 而同一报告边界写 ≈1×。分母一律 = **pass 数** (含 prefill)。
/// 除零/无样本 ⇒ 返回 0 (打印层再决定展示形态), 绝不返回 NaN (NaN 会污染聚合均值)。
/// </summary>
public static class IoThroughput
{
    /// <summary>每 pass 平均字节。passes ≤ 0 ⇒ 0 (不是 NaN)。</summary>
    public static double PerPass(long bytes, int passes) => passes > 0 ? (double)bytes / passes : 0;

    /// <summary>比值。分母 ≤ 0 ⇒ 0。</summary>
    public static double Ratio(long numerator, long denominator) => denominator > 0 ? (double)numerator / denominator : 0;
}
