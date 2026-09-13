using System.Diagnostics;
using System.IO.MemoryMappedFiles;
using agent.rover.runtime;

namespace agent.rover.cli;

/// <summary>
/// 裸读吞吐基准子命令 (R402 度量子步骤的**上界参照物**)。
///
/// 存在理由: 没有「同一台机器、同一个文件、同一条内存路径」的裸读吞吐, 「每 token 25.7 s 是盘读等待还是计算」
/// 就没有分母 —— 只有拿到 MB/s 才能把「盘读字节数」换算成秒数并与前向读数相减。
///
/// 两种模式 = 两条真实内存路径:
///  · <c>stream</c>: FileStream 顺序读 (read syscall 路径, 页缓存命中不回退块设备);
///  · <c>mmap</c>  : 与本引擎热路径**同一条路** —— 逐页触碰映射视图 (缺页驱动 I/O), 无任何数学运算。
/// 两者都打印 /proc/self/io 差 (read_bytes 是「真的吃了盘」的硬证据, 不是推断)。
/// </summary>
public static class ReadBenchCli
{
    public const string UsageLine =
        "  readbench <file> [--mode stream|mmap] [--chunk-mb 8] [--passes 1] [--json FILE]   裸读吞吐 (盘读上界参照)";

    internal static int Run(string[] a, TextWriter o)
    {
        if (a.Length < 2) { o.WriteLine("error{kind=missing_arg arg=file}"); return 2; }
        string path = a[1];
        if (!File.Exists(path)) { o.WriteLine($"error{{kind=file_not_found path={path}}}"); return 2; }
        string mode = Opt(a, "--mode") ?? "stream";
        if (mode != "stream" && mode != "mmap") { o.WriteLine($"error{{kind=bad_mode mode={mode} allowed=stream,mmap}}"); return 2; }
        int chunkMb = int.Parse(Opt(a, "--chunk-mb") ?? "8");
        int passes = int.Parse(Opt(a, "--passes") ?? "1");
        if (chunkMb <= 0 || passes <= 0) { o.WriteLine("error{kind=bad_arg}"); return 2; }
        string? jsonPath = Opt(a, "--json");

        long fileBytes = new FileInfo(path).Length;
        long totalBytes = 0;
        double totalMs = 0;
        var perPassMs = new List<double>(passes);
        var perPassRead = new List<long>(passes);
        long checksum = 0;

        for (int p = 0; p < passes; p++)
        {
            var io0 = ProcIoSnapshot.Capture();
            var sw = Stopwatch.StartNew();
            long bytes = mode == "stream" ? ReadStream(path, chunkMb, ref checksum) : TouchMapped(path, ref checksum);
            sw.Stop();
            var io = ProcIoSnapshot.Delta(io0, ProcIoSnapshot.Capture());
            totalBytes += bytes; totalMs += sw.Elapsed.TotalMilliseconds;
            perPassMs.Add(sw.Elapsed.TotalMilliseconds);
            perPassRead.Add(io.ReadBytes);
            double mbps = bytes / 1048576.0 / Math.Max(1e-9, sw.Elapsed.TotalSeconds);
            o.WriteLine($"readbench_pass{{pass={p} mode={mode} bytes={bytes} ms={sw.Elapsed.TotalMilliseconds:F1} " +
                        $"mb_per_s={mbps:F1} disk_read_bytes={io.ReadBytes} rchar_bytes={io.RcharBytes} " +
                        $"majflt={io.MajFlt} minflt={io.MinFlt} io_counters_available={io.Available}}}");
        }

        double totalMbps = totalBytes / 1048576.0 / Math.Max(1e-9, totalMs / 1000.0);
        bool diskEngaged = perPassRead.Any(r => r > 0);
        o.WriteLine($"readbench{{file={Path.GetFileName(path)} file_bytes={fileBytes} mode={mode} chunk_mb={chunkMb} " +
                    $"passes={passes} bytes_total={totalBytes} ms_total={totalMs:F1} mb_per_s={totalMbps:F1} " +
                    $"checksum={checksum}}}");
        o.WriteLine($"readbench_scope{{disk_read_bytes_first_pass={perPassRead.FirstOrDefault()} " +
                    $"disk_read_bytes_last_pass={perPassRead.LastOrDefault()} " +
                    // 「机制启用断言」: 若 read_bytes 恒 0, 说明这次跑的是页缓存 —— 数字不能当盘吞吐用 (skill: 机制未触发 ⇒ 读数作废)
                    $"disk_path_engaged={diskEngaged} " +
                    $"verdict={(diskEngaged ? "cold_or_thrashing_read_measured" : "page_cache_resident_measurement_discard")} " +
                    $"honest_note=ram_total_must_be_compared_to_file_bytes}}");
        o.WriteLine($"done{{command=readbench mode={mode}}}");

        if (jsonPath is not null)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(jsonPath))!);
            File.WriteAllText(jsonPath,
                "{\"schema\":\"rover-readbench/1\",\"file\":\"" + path + "\",\"file_bytes\":" + fileBytes +
                ",\"mode\":\"" + mode + "\",\"chunk_mb\":" + chunkMb + ",\"passes\":" + passes +
                ",\"per_pass_ms\":[" + string.Join(",", perPassMs.Select(m => m.ToString("F1"))) + "]" +
                ",\"per_pass_disk_read_bytes\":[" + string.Join(",", perPassRead) + "]" +
                ",\"mb_per_s\":" + totalMbps.ToString("F1") + ",\"checksum\":" + checksum +
                ",\"disk_path_engaged\":" + (diskEngaged ? "true" : "false") + "}\n");
        }
        return 0;
    }

    /// <summary>FileStream 顺序读 (read syscall 路径)。缓冲区复用 ⇒ 不把文件读进托管堆。</summary>
    private static long ReadStream(string path, int chunkMb, ref long checksum)
    {
        var buf = new byte[(long)chunkMb * 1048576];
        long bytes = 0;
        using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20, FileOptions.SequentialScan);
        int n;
        while ((n = fs.Read(buf, 0, buf.Length)) > 0)
        {
            bytes += n;
            checksum += buf[0] + buf[n - 1];   // 防优化消除; 只取首尾字节, 成本 O(1)
        }
        return bytes;
    }

    /// <summary>mmap 逐页触碰 (缺页驱动 I/O, 与本引擎同一条内存路径)。</summary>
    private static long TouchMapped(string path, ref long checksum)
    {
        unsafe
        {
            using var mmf = MemoryMappedFile.CreateFromFile(path, FileMode.Open, null, 0, MemoryMappedFileAccess.Read);
            using var view = mmf.CreateViewAccessor(0, 0, MemoryMappedFileAccess.Read);
            byte* p = null;
            view.SafeMemoryMappedViewHandle.AcquirePointer(ref p);
            try
            {
                long len = new FileInfo(path).Length;
                for (long off = 0; off < len; off += 4096)
                    checksum += p[off];
                return len;
            }
            finally { view.SafeMemoryMappedViewHandle.ReleasePointer(); }
        }
    }

    private static string? Opt(string[] a, string name)
    {
        for (int i = 0; i < a.Length - 1; i++) if (a[i] == name) return a[i + 1];
        return null;
    }
}
