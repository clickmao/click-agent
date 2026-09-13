using System.Diagnostics;
using clickrover.gpu;
using clickrover.gpu.spirv;

namespace clickrover.cli;

/// <summary>
/// `vulkan` 子命令 —— GPU 路径的真机证据入口 (零 shell / 零反射 / AOT 友好)。
/// 三层证据, 逐层可核对:
///   ① SPIR-V 结构自检 (独立校验器 + 5 个负向控制组) —— 不需要 GPU, 也必须绿;
///   ② 设备枚举 (真 ICD; 无设备则给机器可读原因, 绝不伪装);
///   ③ 真派发三个引擎内核 (fma_vec / silu_mul / scale_inplace) 与 CPU 参考对账 + 带宽读数。
/// </summary>
public static class VulkanCli
{
    public const string UsageLine =
        "  vulkan [--list] [--device I] [--elements N] [--repeat R] [--spirv-only]   GPU 后端真机对账";

    public static int Run(string[] a, TextWriter o)
    {
        int device = IntOpt(a, "--device", 0);
        int elements = IntOpt(a, "--elements", 8192);
        int repeat = IntOpt(a, "--repeat", 1);

        // ① SPIR-V 结构自检 + 负向控制组 (与汇编器独立实现)
        var kernels = new[] { Kernels.FmaVec(), Kernels.SiluMul(), Kernels.ScaleInPlace() };
        int spirvValid = 0, negDetected = 0, negTotal = 0;
        foreach (var k in kernels)
        {
            var issues = SpirvValidator.Validate(k.Words, (int)k.LocalSizeX, k.BufferCount);
            bool ok = issues.Count == 0;
            if (ok) spirvValid++;
            o.WriteLine($"spirvcheck{{kernel={k.Name} words={k.Words.Length} local_size={k.LocalSizeX} buffers={k.BufferCount} valid={(ok ? "true" : "false")} issues={issues.Count}}}");
            foreach (var i in issues) o.WriteLine($"spirvissue{{kernel={k.Name} code={i.Code} word={i.WordIndex} detail=\"{i.Detail}\"}}");
        }
        foreach (var nc in NegativeControls(kernels[0]))
        {
            negTotal++;
            var got = SpirvValidator.Validate(nc.Words, nc.LocalSize, nc.Buffers);
            bool detected = got.Any(x => x.Code == nc.ExpectCode);
            if (detected) negDetected++;
            o.WriteLine($"spirvneg{{case={nc.Name} expect={nc.ExpectCode} detected={(detected ? "true" : "false")} issues={got.Count}}}");
        }
        if (spirvValid != kernels.Length || negDetected != negTotal)
        {
            o.WriteLine($"error{{kind=spirv_selfcheck_failed valid={spirvValid}/{kernels.Length} neg={negDetected}/{negTotal}}}");
            return 1;
        }
        if (Has(a, "--spv-dump"))
        {
            foreach (var k in new[] { Kernels.FmaVec(), Kernels.SiluMul(), Kernels.ScaleInPlace(), Kernels.DiagProbe() })
            {
                o.WriteLine($"spvdump{{kernel={k.Name} buffers={k.BufferCount} local_size={k.LocalSizeX}}}");
                o.Write(SpvDisassembler.Decode(k.Words));
            }
        }
        if (Has(a, "--spirv-only"))
        {
            o.WriteLine($"done{{command=vulkan mode=spirv_only valid={spirvValid} neg={negDetected}/{negTotal}}}");
            return 0;
        }

        // ② 设备枚举 (真 ICD)
        var devices = VulkanBackend.Enumerate(o, out _, out int count);
        foreach (var d in devices)
            o.WriteLine($"vkdevice{{index={d.Index} name=\"{d.Name}\" api={Ver(d.ApiVersion)} type={d.Type} vendor=0x{d.VendorId:X} families={d.QueueFamilies} compute_family={d.ComputeFamily} mem_bytes={d.MemoryBytes}}}");
        o.WriteLine($"vk{{loader=silk.net.vulkan devices={count}}}");

        if (Has(a, "--list"))
        {
            o.WriteLine($"done{{command=vulkan mode=list devices={count}}}");
            return count > 0 ? 0 : 1;
        }

        using var backend = VulkanBackend.TryOpen(o, device);
        if (backend is null)
        {
            o.WriteLine($"done{{command=vulkan mode=dispatch ok=false reason=device_unavailable}}");
            return 1;
        }

        // ③ 真派发 + CPU 参考对账
        int pass = 0, fail = 0;
        foreach (var k in kernels)
        {
            var (buffers, reference, tol, flops) = Fixture(k.Name, elements);
            int outIdx = k.Name == "scale_inplace" ? 0 : buffers.Length - 1;
            VulkanBackend.DispatchResult last = null!;
            for (int r = 0; r < Math.Max(1, repeat); r++)
                last = backend.Dispatch(k, buffers, elements);
            double maxDiff = 0;
            int cmp = Math.Min(elements, buffers[outIdx].Length);
            for (int i = 0; i < cmp; i++) maxDiff = Math.Max(maxDiff, Math.Abs(buffers[outIdx][i] - reference[i]));
            bool ok = maxDiff <= tol;
            if (ok) pass++; else fail++;
            double gflops = flops * elements / Math.Max(0.001, last.DispatchMs) / 1e6;
            o.WriteLine($"dispatch{{kernel={k.Name} elements={elements} groups={last.Groups} device_ms={last.DispatchMs:F3} elem_per_ms={last.ElementsPerMs:F1} gflops={gflops:F3}}}");
            o.WriteLine($"verify{{kernel={k.Name} max_abs_diff={maxDiff:E6} tol={tol:E6} verdict={(ok ? "ok" : "MISMATCH")}}}");
            int show = IntOpt(a, "--show", 0);
            for (int i = 0; i < Math.Min(show, cmp); i++)
                o.WriteLine($"vkdump{{kernel={k.Name} i={i} gpu={buffers[outIdx][i]:G9} cpu={reference[i]:G9} diff={Math.Abs(buffers[outIdx][i] - reference[i]):E3}}}");
        }
        // ④ 诊断探针 (v4): 解耦"动态索引"与"绑定位置" —— 三态可判(全空 / 只落 binding 2 / 全落地)
        //    缓冲顺序必须与 DiagProbe 变量声明顺序一致: 0=src 1=cst 2=dyn 3=dync 4=diag
        var probe = Kernels.DiagProbe();
        {
            var pIssues = SpirvValidator.Validate(probe.Words, (int)probe.LocalSizeX, probe.BufferCount);
            var pe = Math.Max(4, elements);
            var psrc = new float[pe];
            for (int i = 0; i < pe; i++) psrc[i] = (float)(i * 0.5 - 1.0);
            var pcst = new float[pe]; var pdyn = new float[pe]; var pdync = new float[pe]; var pdiag = new float[8];
            Array.Fill(pcst, 999f); Array.Fill(pdyn, 999f); Array.Fill(pdync, 999f);
            var pr = backend.Dispatch(probe, new[] { psrc, pcst, pdyn, pdync, pdiag }, pe);
            int cstHits = 0;
            for (int i = 0; i < 4; i++) if (pcst[i] == 101f + i) cstHits++;
            int dynHits = 0, dynFirstBad = -1;
            for (int i = 0; i < pe; i++) { if (pdyn[i] == 7f) dynHits++; else if (dynFirstBad < 0) dynFirstBad = i; }
            int dyncHits = 0, dyncFirstBad = -1;
            for (int i = 0; i < pe; i++) { if (pdync[i] == (float)i) dyncHits++; else if (dyncFirstBad < 0) dyncFirstBad = i; }
            o.WriteLine($"vkprobe{{const_b1_hits={cstHits}/4 const_b1_ok={(cstHits == 4 ? "true" : "false")} dyn_b2_hits={dynHits}/{pe} dyn_b2_ok={(dynHits == pe ? "true" : "false")} dyn_b2_first_bad={dynFirstBad} dync_b3_hits={dyncHits}/{pe} dync_b3_ok={(dyncHits == pe ? "true" : "false")} dync_b3_first_bad={dyncFirstBad} diag_len={pdiag[0]:G9} expect_len={pe} diag42_ok={(pdiag[1] == 42f ? "true" : "false")} diag_src0_ok={(pdiag[2] == psrc[0] ? "true" : "false")} index_value={pdiag[3]:G9} index_in_range={(pdiag[3] >= 0f && pdiag[3] < pe && pdiag[3] == MathF.Floor(pdiag[3]) ? "true" : "false")} src0={psrc[0]:G9} cst0={pcst[0]:G9} dyn0={pdyn[0]:G9} dync0={pdync[0]:G9} words={probe.Words.Length} valid={(pIssues.Count == 0 ? "true" : "false")} ms={pr.DispatchMs:F3}}}");
            // 见证扫描: 任何"落错地方"都必须被看见 (has7 = 值 7 的出现数, self = 值等于自身下标数)
            foreach (var (bn, arr) in new[] { ("src", psrc), ("cst", pcst), ("dyn", pdyn), ("dync", pdync), ("diag", pdiag) })
            {
                int v7 = 0, f7 = -1, self = 0, fself = -1;
                for (int i = 0; i < arr.Length; i++)
                {
                    if (arr[i] == 7f) { v7++; if (f7 < 0) f7 = i; }
                    if (arr[i] == (float)i) { self++; if (fself < 0) fself = i; }
                }
                o.WriteLine($"vkwitness{{buf={bn} n={arr.Length} has7={v7} first7={f7} self={self} firstself={fself} v0={arr[0]:G9} v1={arr[1]:G9} vlast={arr[arr.Length - 1]:G9}}}");
            }
        }

        o.WriteLine($"done{{command=vulkan kernels={kernels.Length} pass={pass} fail={fail} spirv_valid={spirvValid} neg={negDetected}/{negTotal}}}");
        return fail == 0 ? 0 : 1;
    }

    sealed record NegativeControl(string Name, uint[] Words, int LocalSize, int Buffers, string ExpectCode);

    /// <summary>五个负向控制组: 校验器必须**逐类**抓到 (否则自检无判别力)。</summary>
    static IEnumerable<NegativeControl> NegativeControls(Kernels.Kernel k)
    {
        var magic = (uint[])k.Words.Clone(); magic[0] = 0xDEADBEEF;
        yield return new("bad_magic", magic, (int)k.LocalSizeX, k.BufferCount, "BAD_MAGIC");
        var bound = (uint[])k.Words.Clone(); bound[3] = 1;
        yield return new("bound_too_small", bound, (int)k.LocalSizeX, k.BufferCount, "ID_BOUND_TOO_SMALL");
        var trunc = k.Words.Concat(new[] { (8u << 16) | 61u }).ToArray();
        yield return new("truncated", trunc, (int)k.LocalSizeX, k.BufferCount, "INSTRUCTION_TRUNCATED");
        yield return new("local_size_mismatch", k.Words, 128, k.BufferCount, "LOCAL_SIZE_MISMATCH");
        yield return new("descriptor_count_mismatch", k.Words, (int)k.LocalSizeX, k.BufferCount - 1, "DESCRIPTOR_COUNT_MISMATCH");
    }

    /// <summary>确定性夹具 + 同源 CPU 参考 (与 GPU 结果对账, 不采信自报)。</summary>
    static (float[][] Buffers, float[] Reference, double Tol, double Flops) Fixture(string kernel, int n)
    {
        var rng = new Random(1234);
        float Next() => (float)(rng.NextDouble() * 4.0 - 2.0);
        switch (kernel)
        {
            case "fma_vec":
            {
                var a = new float[n]; var x = new float[n]; var y = new float[n]; var refv = new float[n];
                for (int i = 0; i < n; i++) { a[i] = Next(); x[i] = Next(); y[i] = Next(); refv[i] = a[i] * x[i] + y[i]; }
                return (new[] { a, x, y }, refv, 1e-6, 2);
            }
            case "silu_mul":
            {
                var g = new float[n]; var u = new float[n]; var outv = new float[n]; var refv = new float[n];
                for (int i = 0; i < n; i++)
                {
                    g[i] = Next(); u[i] = Next();
                    refv[i] = (float)(g[i] / (1.0 + Math.Exp(-g[i])) * u[i]);
                }
                return (new[] { g, u, outv }, refv, 1e-5, 5);
            }
            default: // scale_inplace
            {
                var x = new float[n]; var s = new[] { 0.7071f }; var refv = new float[n];
                for (int i = 0; i < n; i++) { x[i] = Next(); refv[i] = x[i] * s[0]; }
                return (new[] { x, s }, refv, 1e-6, 1);
            }
        }
    }

    static bool Has(string[] a, string n) => a.Any(x => x == n);
    static int IntOpt(string[] a, string name, int dflt)
    {
        for (int i = 0; i < a.Length - 1; i++)
            if (a[i] == name && int.TryParse(a[i + 1], out int v)) return v;
        return dflt;
    }
    static string Ver(uint v) => $"{v >> 22}.{(v >> 12) & 0x3FF}.{v & 0xFFF}";
}
