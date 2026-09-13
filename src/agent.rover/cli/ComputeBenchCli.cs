using System.Diagnostics;
using System.Globalization;
using agent.rover.gguf;
using agent.rover.runtime;

namespace agent.rover.cli;

/// <summary>
/// 计算吞吐基准子命令 (R402 步 2: 把「计算」从减法变**直测**)。
///
/// 存在理由: R402 步 1 用「墙钟 − 盘读等待」反推计算占 9.2–17.0 s/pass, 那是**减法估计**。
/// 本命令把权重**整块复制进常驻内存**(此后零盘读), 只跑反量化+点积, 直接给出「每字节权重需要多少秒」
/// ⇒ 用它可把两个杠杆的收益上界算出来: ① 多线程 (1 vs N 线程实测); ② 批 prefill (计算可摊薄)。
///
/// 三条防呆 (全部机器可判, 不靠人看):
///  · 常驻自证: 计时窗口内 /proc/self/io 的 read_bytes 必须为 0 (否则读数里混了盘读 ⇒ 作废);
///  · 逐位不变性: 同一张量在 1 vs N 线程下 y 的**原始位哈希**必须相等 (多线程只改"谁算哪些行");
///  · 按类型分别外推: 文件里每种量化的「每字节成本」不同, 用单类型外推整体会偏 ⇒ 逐类型测 + 按文件内字节数加权求和。
/// 秒表纪律 (R402 步 1 教训: 墙钟同题极差可达 1.57×): 每次重复都记录, 同时给 min/mean/max 与极差比, 只以比值下结论。
/// </summary>
public static class ComputeBenchCli
{
    public const string UsageLine =
        "  computebench <gguf> [--tensor NAME] [--threads 1,2] [--reps 3] [--max-mib 256] [--json FILE]   常驻内存 反量化+点积 吞吐 (计算直测)";

    internal static int Run(string[] a, TextWriter o)
    {
        if (a.Length < 2) { o.WriteLine("error{kind=missing_arg arg=gguf}"); return 2; }
        string path = a[1];
        if (!File.Exists(path)) { o.WriteLine($"error{{kind=file_not_found path={path}}}"); return 2; }
        string? only = Opt(a, "--tensor");
        int[] threadCounts = (Opt(a, "--threads") ?? "1,2").Split(',', StringSplitOptions.RemoveEmptyEntries)
            .Select(s => int.Parse(s.Trim(), CultureInfo.InvariantCulture)).Distinct().OrderBy(x => x).ToArray();
        if (threadCounts.Length == 0 || threadCounts.Any(t => t < 1)) { o.WriteLine("error{kind=bad_arg arg=--threads min=1}"); return 2; }
        int reps = int.Parse(Opt(a, "--reps") ?? "3", CultureInfo.InvariantCulture);
        int maxMib = int.Parse(Opt(a, "--max-mib") ?? "256", CultureInfo.InvariantCulture);
        string? jsonPath = Opt(a, "--json");
        if (reps < 1 || maxMib < 1) { o.WriteLine("error{kind=bad_arg}"); return 2; }

        using var r = GgufReader.Open(path);
        long budget = (long)maxMib * 1048576;
        int minThreads = threadCounts.Min();

        // ---- 逐类型选择被测张量 (每种量化的每字节成本不同 ⇒ 分类型测, 再按文件内该类型字节数加权) ----
        var byType = new Dictionary<GgmlType, (long Bytes, string Name, GgufTensorInfo? T)>();
        long fileTensorBytes = 0;
        foreach (var n in r.TensorNames)
        {
            var t = r.Require(n);
            fileTensorBytes += t.ByteSize;
            bool ok = t.Dims.Length == 2 && t.ByteSize > 0 && t.ByteSize <= budget;
            if (!byType.TryGetValue(t.Type, out var cur)) { byType[t.Type] = (t.ByteSize, ok ? n : "", ok ? t : null); continue; }
            long total = cur.Bytes + t.ByteSize;
            if (ok && (cur.T is null || t.ByteSize > cur.T.ByteSize)) byType[t.Type] = (total, n, t);
            else byType[t.Type] = (total, cur.Name, cur.T);
        }
        var selected = new List<(GgmlType Type, long FileBytes, string Name, GgufTensorInfo T)>();
        if (only is not null)
        {
            var t = r.Require(only);
            if (t.Dims.Length != 2) { o.WriteLine($"error{{kind=bad_arg arg=--tensor reason=not_2d name={only}}}"); return 2; }
            long typeBytes = 0;
            foreach (var n in r.TensorNames) if (r.Require(n).Type == t.Type) typeBytes += r.Require(n).ByteSize;
            selected.Add((t.Type, typeBytes, only, t));
        }
        else
        {
            foreach (var kv in byType)
                if (kv.Value.T is not null) selected.Add((kv.Key, kv.Value.Bytes, kv.Value.Name, kv.Value.T));
            selected = selected.OrderByDescending(s => s.FileBytes).ToList();
        }
        if (selected.Count == 0) { o.WriteLine($"error{{kind=no_benchable_tensor max_mib={maxMib} file_tensor_bytes={fileTensorBytes}}}"); return 2; }

        o.WriteLine($"computebench{{file={Path.GetFileName(path)} file_bytes={r.Mapped.Length} file_tensor_bytes={fileTensorBytes} " +
                    $"types_benchable={selected.Count} max_mib={maxMib} reps={reps} threads=[{string.Join(",", threadCounts)}] " +
                    $"processor_count={Environment.ProcessorCount} scope=resident_weights_compute_only}}");

        var results = new List<BenchResult>();
        foreach (var sel in selected)
        {
            var t = sel.T;
            int cols = (int)t.Dims[0], rows = (int)t.Dims[1];
            long rowBytes = BlockLayout.RowBytes(t.Type, cols);
            if (rowBytes * rows != t.ByteSize) { o.WriteLine($"error{{kind=row_bytes_mismatch tensor={t.Name} row_bytes_x_rows={rowBytes * rows} byte_size={t.ByteSize}}}"); return 1; }

            // 常驻副本: 一次盘读把整张量搬进托管内存; 之后全部计时都发生在 RAM 上 (计时窗口内盘读必须为 0)。
            var ioCopy0 = ProcIoSnapshot.Capture();
            byte[] w = r.TensorWindow(t).ToArray();
            var ioCopy = ProcIoSnapshot.Delta(ioCopy0, ProcIoSnapshot.Capture());
            var x = SyntheticVector(cols, seed: 12345);
            var res = new BenchResult(sel.Type, sel.Name, sel.FileBytes, t.ByteSize, rows, cols);

            o.WriteLine($"compute_tensor{{type={t.Type} name={t.Name} rows={rows} cols={cols} row_bytes={rowBytes} " +
                        $"weight_bytes={t.ByteSize} weight_mib={(double)t.ByteSize / 1048576.0:F1} resident_copy_disk_read_bytes={ioCopy.ReadBytes} " +
                        $"file_bytes_of_type={sel.FileBytes}}}");
            if (ioCopy.ReadBytes == 0)
                o.WriteLine($"compute_warn{{tensor={t.Name} kind=resident_copy_read_zero_bytes " +
                            $"note=weights_were_already_page_resident_copy_was_still_a_real_memcpy copy_rchar_bytes={ioCopy.RcharBytes}}}");

            foreach (int threads in threadCounts)
            {
                var y = new float[rows];
                CpuKernels.GemvParallel(t.Type, w, rows, cols, x, y, threads);   // 预热: JIT + 首次触碰常驻页 + 线程池, 不计时
                var perRep = new List<double>(reps);
                long diskRead = 0, minFlt = 0, majFlt = 0;
                for (int i = 0; i < reps; i++)
                {
                    var io0 = ProcIoSnapshot.Capture();
                    var sw = Stopwatch.StartNew();
                    CpuKernels.GemvParallel(t.Type, w, rows, cols, x, y, threads);
                    sw.Stop();
                    var io = ProcIoSnapshot.Delta(io0, ProcIoSnapshot.Capture());
                    diskRead += io.ReadBytes; minFlt += io.MinFlt; majFlt += io.MajFlt;
                    perRep.Add(sw.Elapsed.TotalMilliseconds);
                }
                double mean = perRep.Average(), min = perRep.Min(), max = perRep.Max();
                double gbPerS = t.ByteSize / 1e9 / Math.Max(1e-9, mean / 1000.0);
                double gflops = 2.0 * rows * cols / 1e9 / Math.Max(1e-9, mean / 1000.0);
                string hash = Fnv1a64(y);
                res.Add(threads, mean, min, max, gbPerS, gflops, hash, diskRead, minFlt, majFlt);
                o.WriteLine($"compute_pass{{type={t.Type} tensor={t.Name} threads={threads} reps={reps} ms_per_pass_mean={mean:F1} " +
                            $"ms_min={min:F1} ms_max={max:F1} spread_ratio={(min > 0 ? max / min : 0):F3} gb_per_s={gbPerS:F3} gflops={gflops:F2} " +
                            $"y_hash={hash} disk_read_bytes={diskRead} minflt={minFlt} majflt={majFlt}}}");
            }
            results.Add(res);

            var hashes = res.Runs.Select(run => run.Hash).Distinct().ToList();
            o.WriteLine($"thread_invariance{{tensor={t.Name} threads=[{string.Join(",", threadCounts)}] distinct_y_hashes={hashes.Count} " +
                        $"bitwise_identical={hashes.Count == 1} verdict={(hashes.Count == 1 ? "identical" : "MISMATCH")}}}");
            double serialMs = res.Runs.First(run => run.Threads == minThreads).MsPerPass;
            double fastestMs = res.Runs.Min(run => run.MsPerPass);
            o.WriteLine($"compute_summary{{type={t.Type} tensor={t.Name} weight_bytes={t.ByteSize} " +
                        string.Join(" ", res.Runs.Select(run => $"t{run.Threads}_ms_per_pass={run.MsPerPass:F1} t{run.Threads}_gb_per_s={run.GbPerS:F3}")) +
                        $" speedup_vs_serial={serialMs / Math.Max(1e-9, fastestMs):F3}x disk_read_bytes_in_timed_window={res.Runs.Sum(run => run.DiskReadBytes)}}}");
            w = null!;
            GC.Collect();
        }

        // ---- 外推: Σ(该类型文件字节 ÷ 该类型每字节耗时) = 单 token 前向的**计算**部分 ----
        foreach (var res in results)
            foreach (int threads in threadCounts)
            {
                double msPerByte = res.Runs.First(run => run.Threads == threads).MsPerPass / res.WeightBytes;
                res.EstimatedMs[threads] = msPerByte * res.FileBytes;
            }
        foreach (int threads in threadCounts)
        {
            double est = results.Sum(res => res.EstimatedMs[threads]);
            o.WriteLine($"compute_extrapolation{{threads={threads} est_compute_ms_per_token={est:F0} est_tokens_per_s={(est > 0 ? 1000.0 / est : 0):F4} " +
                        $"breakdown=[{string.Join(" ", results.Select(res => $"{res.Type}_est_ms={res.EstimatedMs[threads]:F0}"))}] " +
                        $"rule=sum(type_file_bytes / type_ms_per_byte) scope=weight_traffic_only " +
                        $"excludes=[attn_kv_for_1_token, disk_io_by_construction, thread_creation_overhead]}}");
        }
        double estSerial = results.Sum(res => res.EstimatedMs[minThreads]);
        var best = threadCounts.Select(t => (Threads: t, Ms: results.Sum(res => res.EstimatedMs[t]))).OrderBy(p => p.Ms).First();
        o.WriteLine($"compute_verdict{{serial_threads={minThreads} est_ms_per_token_serial={estSerial:F0} best_threads={best.Threads} " +
                    $"est_ms_per_token_best={best.Ms:F0} speedup={(estSerial > 0 ? estSerial / Math.Max(1e-9, best.Ms) : 0):F3}x " +
                    $"honest_note=est_compute_only_must_be_compared_against_measured_forward_wall_ms}}");
        o.WriteLine($"done{{command=computebench types={results.Count} reps={reps}}}");

        if (jsonPath is not null)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(jsonPath))!);
            var sb = new System.Text.StringBuilder();
            var ic = CultureInfo.InvariantCulture;
            sb.Append("{\"schema\":\"rover-computebench/1\",\"file\":\"").Append(path).Append("\",\"file_tensor_bytes\":").Append(fileTensorBytes);
            sb.Append(",\"processor_count\":").Append(Environment.ProcessorCount).Append(",\"reps\":").Append(reps).Append(",\"tensors\":[");
            sb.Append(string.Join(",", results.Select(res =>
                "{\"type\":\"" + res.Type + "\",\"name\":\"" + res.Name + "\",\"file_bytes\":" + res.FileBytes +
                ",\"weight_bytes\":" + res.WeightBytes + ",\"rows\":" + res.Rows + ",\"cols\":" + res.Cols + ",\"runs\":[" +
                string.Join(",", res.Runs.Select(run =>
                    "{\"threads\":" + run.Threads + ",\"ms_per_pass\":" + run.MsPerPass.ToString("F1", ic) +
                    ",\"ms_min\":" + run.MsMin.ToString("F1", ic) + ",\"ms_max\":" + run.MsMax.ToString("F1", ic) +
                    ",\"gb_per_s\":" + run.GbPerS.ToString("F4", ic) + ",\"gflops\":" + run.Gflops.ToString("F3", ic) +
                    ",\"y_hash\":\"" + run.Hash + "\",\"disk_read_bytes\":" + run.DiskReadBytes +
                    ",\"minflt\":" + run.MinFlt + ",\"majflt\":" + run.MajFlt + "}")) + "]}")));
            sb.Append("],\"estimates\":[" + string.Join(",", threadCounts.Select(t =>
                "{\"threads\":" + t + ",\"est_ms_per_token\":" + results.Sum(res => res.EstimatedMs[t]).ToString("F0", ic) + "}")) + "]}\n");
            File.WriteAllText(jsonPath, sb.ToString());
        }
        return 0;
    }

    /// <summary>确定性合成输入向量 (无 RNG/Random 依赖 ⇒ 外部实现可复算同一条输入)。</summary>
    internal static float[] SyntheticVector(int n, int seed)
    {
        var x = new float[n];
        for (int i = 0; i < n; i++)
            x[i] = (float)(Math.Sin((i + seed) * 0.001953125) * 0.5 + Math.Cos((i * 7 + seed) * 0.0009765625) * 0.25);
        return x;
    }

    /// <summary>逐位哈希 (FNV-1a 64 over float 原始位): 与 ForwardCli 同口径, 用于跨线程逐位对账。</summary>
    internal static string Fnv1a64(ReadOnlySpan<float> x)
    {
        ulong h = 14695981039346656037UL;
        foreach (var v in x)
        {
            uint bits = unchecked((uint)BitConverter.SingleToInt32Bits(v));
            for (int b = 0; b < 4; b++) { h ^= (byte)(bits >> (b * 8)); h *= 1099511628211UL; }
        }
        return h.ToString("x16", CultureInfo.InvariantCulture);
    }

    private static string? Opt(string[] a, string name)
    {
        for (int i = 0; i < a.Length - 1; i++) if (a[i] == name) return a[i + 1];
        return null;
    }

    internal readonly record struct RunResult(int Threads, double MsPerPass, double MsMin, double MsMax, double GbPerS, double Gflops,
        string Hash, long DiskReadBytes, long MinFlt, long MajFlt);

    internal sealed class BenchResult
    {
        public BenchResult(GgmlType type, string name, long fileBytes, long weightBytes, int rows, int cols)
        { Type = type; Name = name; FileBytes = fileBytes; WeightBytes = weightBytes; Rows = rows; Cols = cols; }

        public GgmlType Type { get; }
        public string Name { get; }
        public long FileBytes { get; }
        public long WeightBytes { get; }
        public int Rows { get; }
        public int Cols { get; }
        public List<RunResult> Runs { get; } = new();
        public Dictionary<int, double> EstimatedMs { get; } = new();

        public void Add(int threads, double mean, double min, double max, double gbPerS, double gflops, string hash, long diskRead, long minFlt, long majFlt)
            => Runs.Add(new RunResult(threads, mean, min, max, gbPerS, gflops, hash, diskRead, minFlt, majFlt));
    }
}
