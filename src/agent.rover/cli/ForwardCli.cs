using System.Diagnostics;
using System.Globalization;
using agent.rover.gguf;
using agent.rover.infer;
using agent.rover.quant;
using agent.rover.runtime;

namespace agent.rover.cli;

/// <summary>
/// 前向推理子命令。输出行与既有子命令同风格 (机器可读 kv, 走注入的 TextWriter),
/// 所有数字都来自本次真实执行的运算, 无模拟值。
/// </summary>
public static class ForwardCli
{
    public const string UsageLine = "  forward <gguf> --tokens a,b,c [--ctx N] [--dump DIR] [--drop-pages] [--budget-mb N|--budget-kb N|--budget-bytes N] [--no-pin] [--reclaim-per-token] [--threads N]  前向 logits + top-k (--threads>1 = 行分块并行 GEMV, 数值逐位不变)";

    internal static int Forward(string[] a, TextWriter o)
    {
        if (a.Length < 2) { o.WriteLine("error{kind=missing_arg arg=gguf}"); return 2; }
        string path = a[1];
        string? tokArg = Opt(a, "--tokens");
        if (tokArg is null) { o.WriteLine("error{kind=missing_arg arg=--tokens}"); return 2; }
        var tokens = tokArg.Split(',', StringSplitOptions.RemoveEmptyEntries)
            .Select(s => int.Parse(s.Trim(), CultureInfo.InvariantCulture)).ToArray();

        string? dumpDir = Opt(a, "--dump");
        bool dropPages = a.Contains("--drop-pages");
        bool showSteps = a.Contains("--steps");
        bool noPin = a.Contains("--no-pin");
        bool reclaimPerToken = a.Contains("--reclaim-per-token");
        int budgetMb = int.Parse(Opt(a, "--budget-mb") ?? "96", CultureInfo.InvariantCulture);
        int budgetKb = int.Parse(Opt(a, "--budget-kb") ?? "0", CultureInfo.InvariantCulture);
        long budgetBytesOpt = long.Parse(Opt(a, "--budget-bytes") ?? "0", CultureInfo.InvariantCulture);
        // 0/负 一律表示"不设上限"(由 Ledger.BudgetUnlimited 统一声明); 真子张量级预算用 --budget-bytes 表达。
        long budgetBytes = budgetBytesOpt > 0 ? budgetBytesOpt
            : budgetKb > 0 ? (long)budgetKb * 1024 : (long)budgetMb * 1048576;
        int topk = int.Parse(Opt(a, "--topk") ?? "5", CultureInfo.InvariantCulture);
        int headVals = int.Parse(Opt(a, "--head-vals") ?? "8", CultureInfo.InvariantCulture);
        // R402 步 2: GEMV 线程数 (默认 1 = 串行 ⇒ 与改造前逐位一致; >1 只影响速度, 不影响数值 —— 由 --threads 对账行自证)。
        int threads = int.Parse(Opt(a, "--threads") ?? "1", CultureInfo.InvariantCulture);
        if (threads < 1) { o.WriteLine($"error{{kind=bad_arg arg=--threads value={threads} min=1}}"); return 2; }

        long ws0 = Mem();
        var sw = Stopwatch.StartNew();
        using var r = GgufReader.Open(path);
        sw.Stop();
        var cfg = ModelConfig.From(r);
        long ws1 = Mem();

        o.WriteLine($"forward{{file={Path.GetFileName(path)} file_bytes={r.Mapped.Length} " +
                    $"tokens=[{string.Join(",", tokens)}] n_tokens={tokens.Length} data_offset={r.DataSectionOffset}}}");
        foreach (var line in cfg.Lines()) o.WriteLine(line);
        o.WriteLine($"open{{meta_parse_ms={r.ParseMs} header_open_ms={sw.Elapsed.TotalMilliseconds:F1} " +
                    $"header_bytes_read={r.DataSectionOffset} ws_before={ws0} ws_after={ws1}}}");

        int maxPos = int.Parse(Opt(a, "--ctx") ?? Math.Max(tokens.Length, 4).ToString(CultureInfo.InvariantCulture), CultureInfo.InvariantCulture);
        if (maxPos < tokens.Length) maxPos = tokens.Length;

        // --no-pin: 不预判热集 (空 pin 集) ⇒ norm 全部纳入预算 + LRU, 驱逐/回收路径真被走到。
        IReadOnlyCollection<string>? pins = noPin ? Array.Empty<string>() : null;
        using var fp = new ForwardPass(r, cfg, maxPos, budgetBytes, dropPages, pins, reclaimPerToken, threads);
        o.WriteLine($"residency_scope{{budget_bytes={budgetBytes} budget_unlimited={fp.Ledger.BudgetUnlimited} " +
                    $"pin_mode={(noPin ? "none" : "default_norms")} reclaim_each_step={reclaimPerToken}}}");
        o.WriteLine($"threads{{gemv_threads={threads} processor_count={Environment.ProcessorCount} " +
                    $"min_parallel_rows={ForwardPass.ParallelMinRows} mode={(threads > 1 ? "row_partitioned" : "serial_baseline")}}}");
        RopeCrossCheck(cfg, o);

        TextWriter? stepLog = showSteps ? o : null;
        LayerHook? cb = null;
        if (dumpDir is not null)
        {
            Directory.CreateDirectory(dumpDir);
            cb = (layer, ti, span) =>
                WriteF32(Path.Combine(dumpDir, $"hidden_t{ti}_blk{layer}.bin"), span);
        }

        // output_norm 后的向量也要能落盘 → 通过第二次仅做 norm 的方式不可行 (会破坏 cache 语义),
        // 所以这里只落盘逐层 hidden; output_norm 结果由 numpy 侧独立复算。
        var logits = fp.Forward(tokens, stepLog, cb);
        var st = fp.Stats;

        o.WriteLine($"logits{{count={logits.Length} min={logits.Min():R} max={logits.Max():R} " +
                    $"mean={logits.Average():R} stdev={StdDev(logits):R} sum={Sum(logits):R}}}");
        var top = ForwardPass.TopK(logits, topk);
        for (int i = 0; i < top.Length; i++)
            o.WriteLine($"topk{{rank={i + 1} id={top[i].Id} logit={top[i].Logit:R}}}");
        var hd = new List<string>();
        for (int i = 0; i < Math.Min(headVals, logits.Length); i++)
            hd.Add($"[{i}]={logits[i]:R}");
        o.WriteLine($"logits_head{{{string.Join(" ", hd)}}}");
        // 数值不变性见证: 多线程只改「谁算哪些行」, 不改任何行的算式 ⇒ 1 vs N 线程的 logits 必须**逐位相同**。
        // 落一个哈希 + 逐位自证所需的最小数 (linear 值哈希, 不受打印格式影响)。
        o.WriteLine($"logits_hash{{fnv1a64={Fnv1a64(logits)} bitwise_selfcheck_bits={logits.Length * 32} threads={threads}}}");
        o.WriteLine($"last_hidden{{idx0..3=[{logits[0]:R},{logits[1]:R},{logits[2]:R},{logits[3]:R}]}}");

        o.WriteLine($"timing{{embed_ms={st.EmbedMs:F1} attn_ms={st.AttnMs:F1} ffn_ms={st.FfnMs:F1} " +
                    $"out_norm_ms={st.OutNormMs:F1} lm_head_ms={st.LmHeadMs:F1} total_ms={st.TotalMs:F1} " +
                    $"per_token_ms={st.PerTokenMs:F1} layers={cfg.NLayer} tokens={st.TokensProcessed}}}");
        double lmin = st.LayerMs.Min(), lmax = st.LayerMs.Max();
        o.WriteLine($"layer_timing{{min_ms={lmin:F1} max_ms={lmax:F1} mean_ms={st.LayerMs.Average():F1} " +
                    $"is_per_layer={lmin >= 0}}}");
        var hw = ForwardPass.ReadVm();
        o.WriteLine($"mem{{peak_working_set={st.PeakWorkingSetBytes} peak_vmrss={st.PeakVmRssBytes} " +
                    $"vmhwm={hw.VmHwm} vmhwm_mib={hw.VmHwm / 1048576.0:F1} " +
                    $"kv_cache_bytes={st.CachedKvBytes} gc_heap={GC.GetTotalMemory(false)} drop_pages={dropPages}}}");
        foreach (var line in fp.Ledger.Lines()) o.WriteLine(line);
        // 预算诚实性: 只 pin 集本身超预算时 EnforceBudget 会如实停手 (不假装驱逐) ⇒ 账面必须显式标注超限,
        // 不许把"没驱逐"当成"符合预算"。
        bool budgetOk = fp.Ledger.BudgetUnlimited || fp.Ledger.PeakResidentBytes <= budgetBytes;
        o.WriteLine($"residency_verdict{{peak_resident={fp.Ledger.PeakResidentBytes} budget={budgetBytes} " +
                    $"peak_within_budget={budgetOk} evicts={fp.Ledger.EvictCount} reclaims={fp.Ledger.ReclaimCount} " +
                    $"loads={fp.Ledger.LoadCount} hits={fp.Ledger.CacheHits} misses={fp.Ledger.CacheMisses} " +
                    $"hit_rate={fp.Ledger.HitRate:F4} resident_end={fp.ResidentCount} " +
                    $"verdict={(fp.Ledger.BudgetUnlimited ? "budget_unlimited" : budgetOk ? "within_budget" : "budget_exceeded_honest")}}}");
        o.WriteLine($"stream{{tensor_window_bytes_scanned={st.StreamedBytes} file_bytes={r.Mapped.Length} " +
                    $"ratio={(double)st.StreamedBytes / r.Mapped.Length:F3} touched_windows={r.Mapped.TouchedWindows} " +
                    $"passes={st.Passes} streamed_bytes_per_pass={st.StreamedBytesPerPass:F0}}}");
        // R402 度量子步骤: 把「每 token 秒数」拆成盘读 vs 计算。判据是**盘读字节 / 窗口扫描字节**
        // —— ≈1 说明每个 token 都在真正读盘 (页缓存装不下模型), ≪1 说明命中页缓存 (瓶颈在计算)。
        // 阈值 0.5 是**机械分档**不是结论: 最终归因还需与裸读吞吐 (readbench) 相除才成立。
        o.WriteLine($"io{{available={st.Io.Available} disk_read_bytes={st.Io.ReadBytes} " +
                    $"rchar_bytes={st.Io.RcharBytes} syscr={st.Io.Syscr} minflt={st.Io.MinFlt} majflt={st.Io.MajFlt} " +
                    $"passes={st.Passes} disk_read_bytes_per_pass={st.DiskReadBytesPerPass:F0} " +
                    $"streamed_bytes_per_pass={st.StreamedBytesPerPass:F0} disk_read_ratio={st.DiskReadRatio:F3} " +
                    $"majflt_per_pass={(st.Passes > 0 ? (double)st.Io.MajFlt / st.Passes : 0):F0}}}");
        o.WriteLine($"io_scope{{rule=disk_read_ratio>=0.5⇒io_dominant " +
                    $"attribution={(!st.Io.Available ? "unmeasured_io_counters_unavailable" : st.DiskReadRatio >= 0.5 ? "io_dominant_suspect" : "cache_hit_compute_dominant_suspect")} " +
                    $"honest_note=adjudication_requires_readbench_ratio}}");

        if (dumpDir is not null)
        {
            WriteF32(Path.Combine(dumpDir, "logits.bin"), logits);
            var dims = new List<string>
            {
                $"tokens={string.Join(",", tokens)}",
                $"n_layer={cfg.NLayer}", $"hidden={cfg.Hidden}", $"ffn={cfg.Ffn}",
                $"n_head={cfg.NHead}", $"n_head_kv={cfg.NHeadKv}", $"head_dim={cfg.HeadDim}",
                $"value_dim={cfg.ValueDim}", $"rope_dim={cfg.RopeDim}", $"rope_base={cfg.RopeBase:R}",
                $"rope_scaling={cfg.RopeScaling}", $"rope_factor={cfg.RopeFactor:R}",
                $"rms_eps={cfg.RmsEps:R}", $"vocab={cfg.Vocab}", $"tied={cfg.TiedOutput}",
                $"attn_scale={cfg.AttnScale:R}", $"head_tensor={(cfg.HasOutputTensor ? "output.weight" : "token_embd.weight")}",
                $"top1={top[0].Id}", $"top1_logit={top[0].Logit:R}",
            };
            File.WriteAllLines(Path.Combine(dumpDir, "dims.txt"), dims);
            o.WriteLine($"dump{{dir={dumpDir} logits=logits.bin per_layer_hidden=hidden_t{{ti}}_blk{{l}}.bin " +
                        $"tokens={tokens.Length} dims=dims.txt}}");
        }
        o.WriteLine($"done{{command=forward tokens={tokens.Length} vocab={cfg.Vocab} layers={cfg.NLayer}}}");
        return 0;
    }

    /// <summary>
    /// RoPE 交叉验证: 新建的 <see cref="RopeTable"/> (预计算表) 与既有 <see cref="CpuKernels.Rope"/>。
    /// 仅在不涉及 rope scaling 时可比 (既有内核的缩放公式与本实现口径不同, 不做无意义比较)。
    /// 两个实现必须传<b>同一</b>配对约定; 另附负控: 另一约定必须给出不同结果 (防"配对参数被忽略"的空心通过)。
    /// </summary>
    private static void RopeCrossCheck(ModelConfig cfg, TextWriter o)
    {
        if (cfg.RopeScaling != "none" || cfg.RopeDim != cfg.HeadDim)
        {
            o.WriteLine($"rope_check{{skipped=true reason=scaling_or_partial_dim scaling={cfg.RopeScaling} rope_dim={cfg.RopeDim} head_dim={cfg.HeadDim}}}");
            return;
        }
        int heads = cfg.NHead;
        int pos = 7;
        var seed = new float[heads * cfg.HeadDim];
        for (int i = 0; i < seed.Length; i++) seed[i] = (float)Math.Sin(i * 0.017) * 1.5f + 0.25f;

        var a = (float[])seed.Clone();
        var b = (float[])seed.Clone();
        var table = new RopeTable(cfg.RopeDim, cfg.RopeBase, cfg.RopeScaling, cfg.RopeFactor, pos + 1, cfg.RopePairing);
        table.Apply(a, heads, cfg.HeadDim, pos);
        CpuKernels.Rope(b, heads, cfg.HeadDim, pos, cfg.RopeBase, cfg.Ctx, 0f, 0f, 0f, cfg.RopePairing);
        float md = 0;
        for (int i = 0; i < a.Length; i++) md = Math.Max(md, Math.Abs(a[i] - b[i]));
        o.WriteLine($"rope_check{{arch={cfg.Arch} pairing={RopePairings.ToLlamaCppName(cfg.RopePairing)} impl_a=RopeTable impl_b=CpuKernels.Rope n_heads={heads} head_dim={cfg.HeadDim} " +
                    $"rope_dim={cfg.RopeDim} pos={pos} max_abs_diff={md:R} verdict={(md < 1e-5f ? "match" : "MISMATCH")}}}");

        var other = cfg.RopePairing == RopePairing.NormConsecutive ? RopePairing.NeoxHalf : RopePairing.NormConsecutive;
        var c = (float[])seed.Clone();
        new RopeTable(cfg.RopeDim, cfg.RopeBase, cfg.RopeScaling, cfg.RopeFactor, pos + 1, other).Apply(c, heads, cfg.HeadDim, pos);
        float od = 0;
        for (int i = 0; i < c.Length; i++) od = Math.Max(od, Math.Abs(c[i] - a[i]));
        o.WriteLine($"rope_pairing_negctl{{active={RopePairings.ToLlamaCppName(cfg.RopePairing)} other={RopePairings.ToLlamaCppName(other)} max_abs_diff={od:R} " +
                    $"verdict={(od > 0.1f ? "distinct" : "SUSPECT_SAME")}}}");
    }

    private static string? Opt(string[] a, string name)
    {
        for (int i = 0; i < a.Length - 1; i++) if (a[i] == name) return a[i + 1];
        return null;
    }

    private static long Mem()
    {
        using var p = Process.GetCurrentProcess();
        p.Refresh();
        return p.WorkingSet64;
    }

    private static double StdDev(float[] x)
    {
        double m = x.Average(), s = 0;
        foreach (var v in x) { double d = v - m; s += d * d; }
        return Math.Sqrt(s / x.Length);
    }

    private static double Sum(float[] x)
    {
        double s = 0;
        foreach (var v in x) s += v;
        return s;
    }

    /// <summary>logits 的逐位哈希 (FNV-1a 64, 输入是 float 的**原始位**) ⇒ 跨线程数/跨次运行可逐位对账, 不受打印格式影响。</summary>
    internal static string Fnv1a64(ReadOnlySpan<float> x)
    {
        ulong h = 14695981039346656037UL;
        foreach (var v in x)
        {
            uint bits = unchecked((uint)BitConverter.SingleToInt32Bits(v));
            for (int b = 0; b < 4; b++)
            {
                h ^= (byte)(bits >> (b * 8));
                h *= 1099511628211UL;
            }
        }
        return h.ToString("x16", CultureInfo.InvariantCulture);
    }

    private static void WriteF32(string path, ReadOnlySpan<float> data)
    {
        var bytes = new byte[data.Length * 4];
        for (int i = 0; i < data.Length; i++)
            BitConverter.TryWriteBytes(bytes.AsSpan(i * 4, 4), data[i]);   // 小端: 与 numpy '<f4' 一致
        File.WriteAllBytes(path, bytes);
    }
}
