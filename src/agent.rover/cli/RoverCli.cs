using System.Diagnostics;
using agent.rover.gguf;
using agent.rover.formal;
using agent.rover.quant;
using agent.rover.runtime;

namespace agent.rover.cli;

/// <summary>
/// agent.rover CLI (零 shell / 零反射 / AOT 入口)。所有子命令都产出可核对的机器可读行,
/// 供真机证据采集脚本直接抓取 (无 Console.WriteLine — 输出走注入的 TextWriter)。
/// </summary>
public static class RoverCli
{
    public static int Run(string[] args, TextWriter o, TextWriter err)
    {
        if (args.Length == 0) { Usage(o); return 2; }
        try
        {
            return args[0] switch
            {
                "meta" => Meta(args, o),
                "dequant" => DequantCmd(args, o),
                "matvec" => MatVecCmd(args, o),
                "residency" => ResidencyCmd(args, o),
                "probe" => Probe(args, o),
                "check" => CheckCmd(args, o),
                "forward" => ForwardCli.Forward(args, o),
                "tokenize" or "generate" => GenerateCli.Run(args, o),
                "vulkan" => VulkanCli.Run(args, o),
                "embed" => EmbedCli.Run(args, o),
                "readbench" => ReadBenchCli.Run(args, o),
                "computebench" => ComputeBenchCli.Run(args, o),
                "--help" or "-h" or "help" => Usage(o),
                _ => Unknown(args[0], err),
            };
        }
        catch (Exception ex)
        {
            err.WriteLine($"error{{kind={ex.GetType().Name} message={ex.Message}}}");
            return 1;
        }
    }

    private static int Unknown(string cmd, TextWriter err)
    {
        err.WriteLine($"error{{kind=unknown_command command={cmd}}}");
        return 2;
    }

    private static int Usage(TextWriter o)
    {
        o.WriteLine("agent.rover — 本地 GGUF 推理引擎 (mmap 惰性 / 热集驻留 / CPU+GPU 混合)");
        o.WriteLine("  meta <gguf> [--tensors]          元数据 + 张量目录 (含量化类型分布)");
        o.WriteLine("  dequant <gguf> <tensor> [--rows N] [--out f32.bin] [--json]");
        o.WriteLine("  matvec <gguf> <tensor> [--seed N] [--repeat N] [--ablate]");
        o.WriteLine("  residency <gguf> [--budget-mb N] [--pin a,b]  驻留/回收账");
        o.WriteLine("  residency --selftest <gguf>                  驻留/回收自证套件 (含负向控制组)");
        o.WriteLine("  probe <gguf>                     综合证据 (惰性加载 + 驻留 + 回收)");
        o.WriteLine("  check <file.assert> [--json]     本地形式化裁决 (可判定片段 / 零 token / 零 shell)");
        o.WriteLine("  check --selftest                 内核自证套件 (含反例控制组)");
        o.WriteLine(ForwardCli.UsageLine);
        o.WriteLine(GenerateCli.UsageLine);
        o.WriteLine(VulkanCli.UsageLine);
        o.WriteLine(EmbedCli.UsageLine);
        o.WriteLine(ReadBenchCli.UsageLine);
        o.WriteLine(ComputeBenchCli.UsageLine);
        return 0;
    }

    private static string? Opt(string[] a, string name)
    {
        for (int i = 0; i < a.Length - 1; i++) if (a[i] == name) return a[i + 1];
        return null;
    }

    private static int Meta(string[] a, TextWriter o)
    {
        if (a.Length < 2) { o.WriteLine("error{kind=missing_arg arg=gguf}"); return 2; }
        string path = a[1];
        long ws0 = Mem();
        using var r = GgufReader.Open(path);
        long ws1 = Mem();

        o.WriteLine($"gguf{{file={Path.GetFileName(path)} bytes={r.Mapped.Length} version={r.Version} tensors={r.TensorCount} kv={r.KvCount} alignment={r.Alignment} data_offset={r.DataSectionOffset}}}");
        o.WriteLine($"mmap{{parse_ms={r.ParseMs} working_set_before={ws0} after={ws1} delta={ws1 - ws0} touched_windows={r.Mapped.TouchedWindows}}}");
        string[] archKeys = { "general.architecture", "general.name", "general.file_type", "general.quantization_version" };
        foreach (var k in archKeys)
            if (r.GetString(k) is { } s) o.WriteLine($"kv{{key={k} value={s}}}");
        string arch = r.GetString("general.architecture") ?? "unknown";
        (string, string)[] nums =
        {
            ($"{arch}.block_count", "layers"), ($"{arch}.context_length", "ctx"),
            ($"{arch}.embedding_length", "hidden"), ($"{arch}.feed_forward_length", "ffn"),
            ($"{arch}.attention.head_count", "heads"), ($"{arch}.attention.head_count_kv", "kv_heads"),
            ($"{arch}.attention.layer_norm_rms_epsilon", "rms_eps"),
            ($"{arch}.rope.freq_base", "rope_base"), ($"{arch}.rope.scaling.factor", "rope_factor"),
            ($"{arch}.rope.scaling.type", "rope_type"), ($"{arch}.attention.key_length", "key_len"),
            ($"{arch}.attention.value_length", "value_len"),
        };
        foreach (var (k, label) in nums)
        {
            if (r.TryGetLong(k, out var v)) o.WriteLine($"cfg{{key={label} value={v} raw=u}}");
            else if (r.TryGetFloat(k, out var f)) o.WriteLine($"cfg{{key={label} value={f:F6} raw=f}}");
            else if (r.GetString(k) is { } s) o.WriteLine($"cfg{{key={label} value={s} raw=s}}");
        }

        // 词表大小 (不物化字符串数组: 只读计数)
        if (r.Kv.TryGetValue("tokenizer.ggml.tokens", out var tv) && tv.A is { } arr)
            o.WriteLine($"cfg{{key=vocab value={arr.Count}}}");

        // 量化类型分布 = Q4_K_M 配方证据 (哪些张量被提升到 Q6_K/Q8_0)
        var byType = r.TensorNames.GroupBy(n => r.Require(n).Type).OrderByDescending(g => g.Count());
        long totalBytes = 0;
        foreach (var g in byType)
        {
            long bytes = g.Sum(n => r.Require(n).ByteSize);
            totalBytes += bytes;
            o.WriteLine($"quants{{type={g.Key} tensors={g.Count()} bytes={bytes} share={(double)bytes / r.Mapped.Length:P1}}}");
        }
        o.WriteLine($"quants{{total_tensor_bytes={totalBytes} file_bytes={r.Mapped.Length}}}");

        if (a.Contains("--tensors"))
        {
            foreach (var n in r.TensorNames)
            {
                var t = r.Require(n);
                o.WriteLine($"tensor{{name={n} type={t.Type} dims=[{string.Join(",", t.Dims)}] elems={t.ElementCount} bytes={t.ByteSize} offset={t.Offset}}}");
            }
        }
        o.WriteLine($"done{{command=meta tensors={r.TensorCount}}}");
        return 0;
    }

    private static int DequantCmd(string[] a, TextWriter o)
    {
        if (a.Length < 3) { o.WriteLine("error{kind=missing_arg need=tensor}"); return 2; }
        int rows = int.Parse(Opt(a, "--rows") ?? "1");
        string? outFile = Opt(a, "--out");
        using var r = GgufReader.Open(a[1]);
        var t = r.Require(a[2]);
        if (!BlockLayout.IsDequantizable(t.Type)) throw new NotSupportedException($"dequant_not_implemented: {t.Type}");
        int cols = (int)t.RowElems;
        var sw = Stopwatch.StartNew();
        var dst = new float[cols];
        var all = new float[(long)rows * cols];
        var window = r.TensorWindow(t);
        for (int i = 0; i < rows; i++)
        {
            Dequant.RowAt(t.Type, window, i, cols, dst);
            Array.Copy(dst, 0, all, (long)i * cols, cols);
        }
        sw.Stop();
        double sum = 0, sumsq = 0, min = double.MaxValue, max = double.MinValue;
        foreach (var v in all) { sum += v; sumsq += (double)v * v; if (v < min) min = v; if (v > max) max = v; }
        o.WriteLine($"dequant{{tensor={t.Name} type={t.Type} dims=[{string.Join(",", t.Dims)}] rows={rows} cols={cols} ms={sw.Elapsed.TotalMilliseconds:F1}}}");
        o.WriteLine($"stats{{sum={sum:R} sumsq={sumsq:R} min={min:R} max={max:R} mean={sum / all.Length:R}}}");
        if (outFile != null)
        {
            var bytes = new byte[all.Length * 4];
            Buffer.BlockCopy(all, 0, bytes, 0, bytes.Length);
            File.WriteAllBytes(outFile, bytes);
            o.WriteLine($"out{{file={outFile} bytes={bytes.Length}}}");
        }
        o.WriteLine($"done{{command=dequant elements={all.Length}}}");
        return 0;
    }

    private static int MatVecCmd(string[] a, TextWriter o)
    {
        if (a.Length < 3) { o.WriteLine("error{kind=missing_arg need=tensor}"); return 2; }
        int seed = int.Parse(Opt(a, "--seed") ?? "42");
        int repeat = int.Parse(Opt(a, "--repeat") ?? "1");
        bool ablate = a.Contains("--ablate");
        using var r = GgufReader.Open(a[1]);
        var t = r.Require(a[2]);
        int cols = (int)t.RowElems, rows = (int)t.Rows;
        var x = new float[cols];
        var rnd = new Random(seed);
        double xn = 0;
        for (int i = 0; i < cols; i++) { x[i] = (float)(rnd.NextDouble() * 2 - 1); xn += (double)x[i] * x[i]; }
        o.WriteLine($"matvec{{tensor={t.Name} type={t.Type} rows={rows} cols={cols} weight_bytes={t.ByteSize} x_norm2={xn:R}}}" +
                    $"\n  # weight 是 {ResidencyLedger.Fmt(t.ByteSize)} 的量化张量: 融合路径不物化整张量");

        var y = new float[rows];
        long ws0 = Mem();
        var window = r.TensorWindow(t);
        var sw = Stopwatch.StartNew();
        for (int i = 0; i < repeat; i++) CpuKernels.Gemv(t.Type, window, rows, cols, x, y);
        sw.Stop();
        long ws1 = Mem();
        double ysum = 0; foreach (var v in y) ysum += v;
        o.WriteLine($"fused{{repeat={repeat} ms={sw.Elapsed.TotalMilliseconds:F1} ms_per_pass={sw.Elapsed.TotalMilliseconds / repeat:F1} gflops={2.0 * rows * cols * repeat / (sw.Elapsed.TotalSeconds * 1e9):F3} y_sum={ysum:R} ws_delta={(ws1 - ws0) / 1024.0:F0}KiB}}");

        if (ablate)
        {
            var y2 = new float[rows];
            long wsA0 = Mem();
            long rowBytes = (long)cols * 4;
            CpuKernels.GemvMaterialized(t.Type, window, rows, cols, x, y2, _ => { });
            long wsA1 = Mem();
            double maxDiff = 0;
            for (int i = 0; i < rows; i++) maxDiff = Math.Max(maxDiff, Math.Abs(y[i] - y2[i]));
            o.WriteLine($"ablation{{mode=materialized row_buffer_bytes={rowBytes} ws_delta={(wsA1 - wsA0) / 1024.0:F0}KiB max_abs_diff_vs_fused={maxDiff:R}}}");
        }
        o.WriteLine($"done{{command=matvec rows={rows}}}");
        return 0;
    }

    private static int ResidencyCmd(string[] a, TextWriter o)
    {
        if (a.Length >= 2 && a[1] == "--selftest")
        {
            string? selPath = Opt(a, "--file") ?? Opt(a, "--gguf")
                ?? (a.Length > 2 && !a[2].StartsWith("--", StringComparison.Ordinal) ? a[2] : null);
            if (selPath is null) { o.WriteLine("usage: residency --selftest <gguf>"); return 2; }
            return ResidencySelfTest.Run(selPath, o);
        }
        if (a.Length < 2) { o.WriteLine("error{kind=missing_arg arg=gguf}"); return 2; }
        long budget = long.Parse(Opt(a, "--budget-mb") ?? "64") * 1024 * 1024;
        var pins = (Opt(a, "--pin") ?? string.Empty).Split(',', StringSplitOptions.RemoveEmptyEntries);
        using var r = GgufReader.Open(a[1]);
        var res = new TensorResidency(r, budget, pins);
        // 顺序取 3 个小张量两次: 第一次 miss+load, 第二次 hit (活性计数)
        var small = r.TensorNames.Where(n => r.Require(n).ElementCount is > 0 and < 1 << 20)
            .OrderBy(n => r.Require(n).ByteSize).Take(3).ToList();
        for (int pass = 0; pass < 2; pass++)
            foreach (var n in small)
            {
                var b = res.AcquireF32(n);
                float s = 0; foreach (var v in b.Span) s += v;
                o.WriteLine($"acquire{{pass={pass} tensor={n} bytes={b.Bytes} pinned={b.Pinned} span_sum={s:R} resident={res.ResidentCount}}}");
            }
        long reclaimed = res.ReclaimAll();
        o.WriteLine($"reclaim{{freed_bytes={reclaimed} resident_after={res.ResidentCount} pinned={string.Join("|", res.PinnedNames)}}}");
        foreach (var line in res.Ledger.Lines()) o.WriteLine(line);
        o.WriteLine($"done{{command=residency}}");
        return 0;
    }

    private static int Probe(string[] a, TextWriter o)
    {
        if (a.Length < 2) { o.WriteLine("error{kind=missing_arg arg=gguf}"); return 2; }
        string path = a[1];
        long ws0 = Mem();
        var swOpen = Stopwatch.StartNew();
        using var r = GgufReader.Open(path);
        swOpen.Stop();
        long ws1 = Mem();
        o.WriteLine($"probe{{file={Path.GetFileName(path)} file_bytes={new FileInfo(path).Length} open_meta_ms={swOpen.Elapsed.TotalMilliseconds:F1} ws_before={ws0} ws_after={ws1} ws_delta={ws1 - ws0}}}");

        // 惰性证据: 打开后工作集增量应远小于文件大小 (只读头部)
        double ratio = new FileInfo(path).Length == 0 ? 0 : (double)(ws1 - ws0) / new FileInfo(path).Length;
        o.WriteLine($"lazy{{ws_delta_over_file={ratio:P4} verdict={(ratio < 0.35 ? "lazy_ok" : "suspect_eager_read")}}}");

        var biggest = r.TensorNames.OrderByDescending(n => r.Require(n).ByteSize).First();
        var bt = r.Require(biggest);
        // 只读该张量的前 2 行 → 触页量应为 2 行而不是整张量
        int cols = (int)bt.RowElems;
        var buf = new float[cols];
        long wsBefore = Mem();
        var window = r.TensorWindow(bt);
        Dequant.RowAt(bt.Type, window, 0, cols, buf);
        long wsAfter = Mem();
        o.WriteLine($"lazy_touch{{tensor={biggest} type={bt.Type} tensor_bytes={bt.ByteSize} row0_cols={cols} ws_delta={(wsAfter - wsBefore) / 1024.0:F0}KiB first_val={buf[0]:R}}}");
        o.WriteLine($"done{{command=probe}}");
        return 0;
    }

    // ── 形式化裁决 (可判定片段 / 零 token / 零外部进程) ────────────────────────────

    private static int CheckCmd(string[] args, TextWriter o)
    {
        if (args.Length < 2) { o.WriteLine("usage: check <file.assert> [--json] | check --selftest"); return 2; }
        if (args[1] == "--selftest") return CheckSelfTest(o);

        string path = args[1];
        bool json = args.Contains("--json");
        var r = FormalKernel.CheckText(File.ReadAllText(path));
        if (json) o.WriteLine(FormalKernel.Json(r));
        else
        {
            o.WriteLine($"formal{{file={Path.GetFileName(path)} verdict={r.Verdict} exit_code={r.ExitCode} vars={r.Vars} cases={r.Cases} ms={r.Ms:F3} tokens=0 note={r.Note}}}");
            if (r.Counterexample != null)
            {
                var sb = new System.Text.StringBuilder();
                foreach (var kv in r.Counterexample) { if (sb.Length > 0) sb.Append(' '); sb.Append(kv.Key).Append('=').Append(kv.Value); }
                o.WriteLine($"counterexample{{{sb}}}");
            }
        }
        return r.ExitCode;
    }

    /// <summary>内核自证: 正向(必须证明) + **反向控制**(必须不证明/必须 Unknown)。任一不符即失败。</summary>
    private static int CheckSelfTest(TextWriter o)
    {
        var cases = new (string Id, string Text, Verdict Expected)[]
        {
            ("proved_interval",     "premise x >= 0\npremise x <= 10\ngoal x <= 20\n", Verdict.Proved),
            ("refuted_strictness",  "premise x >= 0\ngoal x > 0\n", Verdict.Refuted),
            ("proved_arith",        "premise x >= 0\npremise y == x + 1\ngoal y >= 1\n", Verdict.Proved),
            ("refuted_eq",          "premise x == 3\ngoal x == 4\n", Verdict.Refuted),
            ("vacuous_premises",    "premise x > 5\npremise x < 3\ngoal x == 99\n", Verdict.Vacuous),
            // R388 语义修正: 片段外(非线性) ⇒ **Unknown 诚实弃权** —— 绝不可记为 Malformed,
            // 否则 DCR 会把「正确弃权」当成「畸形」, 反向污染合规率口径
            ("unknown_nonlinear",   "premise x >= 0\ngoal x * y > 0\n", Verdict.Unknown),
            // 负向控制: 真·语法错必须仍是 Malformed (不能因上面的放宽而漏判)
            ("malformed_missing_operand", "premise x >=\ngoal x > 0\n", Verdict.Malformed),
            ("proved_disjunction",  "premise a: x <= 0\ngoal x <= 0 || x >= 1\n", Verdict.Proved),
            ("unknown_fragment",    "premise v1 >= 0\npremise v2 >= 0\npremise v3 >= 0\npremise v4 >= 0\npremise v5 >= 0\npremise v6 >= 0\npremise v7 >= 0\npremise v8 >= 0\npremise v9 >= 0\npremise v10 >= 0\npremise v11 >= 0\npremise v12 >= 0\npremise v13 >= 0\ngoal v1 + v2 + v3 + v4 + v5 + v6 + v7 + v8 + v9 + v10 + v11 + v12 + v13 >= 0\n", Verdict.Unknown),
            ("refuted_control_implication", "premise x <= 5\ngoal x <= 4\n", Verdict.Refuted),
            ("proved_integer_edge", "premise x < 3\ngoal x <= 2\n", Verdict.Proved),
            ("vacuous_int_infeasible_premises", "premise 2*x == 3\ngoal x >= 0\n", Verdict.Vacuous),
            // 回归: z3 独立对账抓出的不健全 bug —— 等式 × strict 交互 (Combine 乘子为 0 会凭空产出 0<0)
            ("refuted_eq_strict_mix", "premise x + y == 10\npremise x >= 0\npremise y >= 0\ngoal x <= 4\n", Verdict.Refuted),
            ("proved_strict_bound_from_eq", "premise x + y == 10\npremise x > 4\ngoal x >= 5\n", Verdict.Proved),
        };

        int pass = 0, fail = 0;
        foreach (var (id, text, expected) in cases)
        {
            var r = FormalKernel.CheckText(text);
            bool ok = r.Verdict == expected;
            // 反例控制: Refuted 必须给出**精确复核过的**反例模型, 否则视为失败
            if (ok && expected == Verdict.Refuted && r.Counterexample == null) ok = false;
            if (ok) pass++; else fail++;
            o.WriteLine($"case{{id={id} expected={expected} actual={r.Verdict} evidence={(r.Counterexample == null ? "-" : "model")} ms={r.Ms:F3} verdict={(ok ? "ok" : "FAIL")}}}");
        }
        o.WriteLine($"selftest{{ran={cases.Length} pass={pass} fail={fail} tokens=0 engine={FormalKernel.Engine}}}");
        return fail == 0 ? 0 : 1;
    }

    private static long Mem()
    {
        using var p = Process.GetCurrentProcess();
        p.Refresh();
        return p.WorkingSet64;
    }
}
