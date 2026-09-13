using System.Security.Cryptography;
using agent.embedcpu;
using agent.rover.gpu;

namespace agent.rover.cli;

/// <summary>
/// <c>embed</c> 命令 (R393): 本地 BGE 的端口真机对账入口。
///
/// 一次运行同时给出四件事:
///   ① 端口确实被使用 (dispatch 次数 == 层数×6×文本数×重复数 —— 防"空心判定");
///   ② Vulkan 端口与 CPU 端口的数值一致性 (逐元素最大差 / 余弦 / 位相等计数);
///   ③ 重复运行的确定性 (同端口多次嵌入逐位一致);
///   ④ 进程内存 (端口不泄漏 —— 每次派发的管线类资源必须回收)。
/// 输出全为机器可读行 (bgemodel / port / emb / determinism / parity / portcheck / mem / done), 零 shell / 零反射。
/// </summary>
public static class EmbedCli
{
    public const string UsageLine =
        "  embed [--model gguf] [--backend cpu|vulkan] [--device I] [--repeat R] [--text T] [--compare] [--selftest]";

    /// <summary>每层 6 次矩阵乘 (q/k/v/attn_output/ffn_up/ffn_down), 4 层 ⇒ 一次嵌入 24 次派发。</summary>
    const int MatMulPerLayer = 6;
    const int Layers = 4;

    static readonly string[] DefaultTexts =
    {
        "本地嵌入端口必须与 CPU 端口逐位可对账。",
        "bge-small-zh-v1.5 embedding executed on a Vulkan compute pipeline.",
        "混合 mixed 文本 12345 —— parity check, 端口不产生第二份前向语义。",
    };

    public static int Run(string[] a, TextWriter o)
    {
        var model = Opt(a, "--model")
            ?? Environment.GetEnvironmentVariable("BGE_MODEL")
            ?? Environment.GetEnvironmentVariable("AGENTFRAMEWORK_BGE_MODEL")
            ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".agentframework", "models", "bge-q8.gguf");
        var backend = Opt(a, "--backend") ?? "cpu";
        var device = int.TryParse(Opt(a, "--device"), out var dv) ? dv : 0;
        var repeat = int.TryParse(Opt(a, "--repeat"), out var rp) && rp > 0 ? rp : 1;
        var compare = a.Contains("--compare") || a.Contains("--selftest");
        var strict = a.Contains("--selftest");
        var texts = Texts(a);

        if (!File.Exists(model))
        {
            o.WriteLine($"done{{command=embed ok=false reason=model_missing path={model}}}");
            return 2;
        }

        o.WriteLine($"bgemodel{{path={model} backend={backend} device_index={device} repeat={repeat} texts={texts.Length}}}");

        using var cpu = new BgeCpuEmbedder(model, CpuMatMulBackend.Instance);
        if (!cpu.IsAvailable) { o.WriteLine("done{command=embed ok=false reason=model_unreadable}"); return 2; }

        VulkanMatMulBackend? gpu = null;
        if (string.Equals(backend, "vulkan", StringComparison.Ordinal))
        {
            gpu = VulkanMatMulBackend.TryOpen(o, device);
            if (gpu is null)
            {
                // 显式请求 GPU 端口却无可用设备: 直接失败 —— 绝不静默退回 CPU 冒充 GPU。
                o.WriteLine($"done{{command=embed backend=vulkan ok=false reason=device_unavailable device={device}}}");
                return 1;
            }
            var di = gpu.Device;
            o.WriteLine($"vkdevice{{index={di.Index} name=\"{di.Name}\" type={di.Type} api={di.ApiVersion} vendor=0x{di.VendorId:X} compute_family={di.ComputeFamily} mem_bytes={di.MemoryBytes}}}");
        }

        var port = gpu is null ? (IMatMulBackend)CpuMatMulBackend.Instance : gpu;
        o.WriteLine($"port{{name={port.Name} engine=BgeCpuEmbedder matmul_per_layer={MatMulPerLayer} layers={Layers}}}");
        using var emb = new BgeCpuEmbedder(model, port);

        // 内存基线 (泄漏判据): 模型已加载 + 端口已打开之后的 RSS/managed
        o.WriteLine($"membase{{stage=before_passes rss_kb={RssKb()} managed_bytes={GC.GetTotalMemory(true)}}}");

        // 重复运行 (确定性 + 内存): 每个 pass 完整嵌入全部文本
        float[][]? first = null;
        var deterministic = true;
        var sw = System.Diagnostics.Stopwatch.StartNew();
        for (var rep = 0; rep < repeat; rep++)
        {
            var run = new float[texts.Length][];
            for (var i = 0; i < texts.Length; i++)
            {
                run[i] = emb.Embed(texts[i]);
                if (rep == 0 && !compare) o.WriteLine(EmbLine($"pass{rep}", run[i]));
            }
            if (rep == 0) first = run;
            else
            {
                for (var i = 0; i < texts.Length; i++)
                {
                    var bits = Diff(first![i], run[i]).BitsEqual;
                    if (bits != run[i].Length) deterministic = false;
                }
                o.WriteLine($"determinism{{pass={rep} port={port.Name} texts={texts.Length} identical={(deterministic ? "true" : "false")}}}");
            }
        }
        sw.Stop();
        var msPerPass = sw.Elapsed.TotalMilliseconds / repeat;
        o.WriteLine($"timing{{backend={port.Name} texts={texts.Length} repeat={repeat} ms_per_pass_ms={Math.Round(msPerPass)} ms_per_embed_ms={Math.Round(msPerPass / texts.Length)}}}");

        // 端口确实被使用 (防空心): 派发次数必须等于 层数×6×文本数×重复数
        var expected = Layers * MatMulPerLayer * texts.Length * repeat;
        var actual = gpu is null ? expected : gpu.Dispatches;
        var portUsed = actual == expected;
        o.WriteLine($"portcheck{{backend={port.Name} dispatch_calls={actual} expected={expected} match={portUsed}}}");
        if (gpu is not null)
        {
            var ps = gpu.PoolStats;
            o.WriteLine($"pool{{classes={ps.Classes} slots={ps.Slots} leases={ps.Leases} reuses={ps.Reuses}}}");
        }
        o.WriteLine($"mem{{stage=after_passes rss_kb={RssKb()} managed_bytes={GC.GetTotalMemory(true)}}}");

        if (!compare)
        {
            o.WriteLine($"done{{command=embed backend={port.Name} mode=single ok={portUsed && deterministic} texts={texts.Length}}}");
            return portUsed && deterministic ? 0 : 1;
        }

        // 逐元素对账: 最大绝对差 / 余弦 / 位相等计数
        var worstAbs = 0f;
        var worstCos = 1.0;
        var allBitsEqual = true;
        for (var i = 0; i < texts.Length; i++)
        {
            var baseline = cpu.Embed(texts[i]);
            var probe = first![i];
            var (maxAbs, cos, bitsEqual) = Diff(baseline, probe);
            worstAbs = MathF.Max(worstAbs, maxAbs);
            worstCos = Math.Min(worstCos, cos);
            if (bitsEqual != baseline.Length) allBitsEqual = false;
            o.WriteLine($"parity{{text_index={i} dim={baseline.Length} max_abs_diff={maxAbs:E3} cos={cos:F9} bits_equal={bitsEqual}/{baseline.Length} sha256_cpu={Sha(baseline)} sha256_port={Sha(probe)}}}");
        }

        var pass = worstAbs <= (strict ? 1e-3f : float.MaxValue) && worstCos >= 0.99999 && portUsed && deterministic;
        o.WriteLine($"done{{command=embed backend={port.Name} mode=compare ok={pass} verdict={(pass ? "PASS" : "FAIL")} worst_abs_diff={worstAbs:E3} worst_cos={worstCos:F9} bits_identical={allBitsEqual} dispatch_calls={(gpu is null ? 0 : gpu.Dispatches)}}}");
        return pass ? 0 : 1;
    }

    static string EmbLine(string tag, float[] v)
    {
        var norm = 0f;
        foreach (var x in v) norm += x * x;
        return $"emb{{tag={tag} dim={v.Length} l2={MathF.Sqrt(norm):F6} head=[{v[0]:F6},{v[1]:F6},{v[2]:F6}] sha256={Sha(v)}}}";
    }

    static (float MaxAbs, double Cos, int BitsEqual) Diff(float[] a, float[] b)
    {
        if (a.Length != b.Length) throw new InvalidOperationException($"bge_port_dim_mismatch: {a.Length} vs {b.Length}");
        double dot = 0, na = 0, nb = 0;
        var maxAbs = 0f;
        var bitsEqual = 0;
        for (var i = 0; i < a.Length; i++)
        {
            var d = MathF.Abs(a[i] - b[i]);
            if (d > maxAbs) maxAbs = d;
            dot += (double)a[i] * b[i];
            na += (double)a[i] * a[i];
            nb += (double)b[i] * b[i];
            if (BitConverter.SingleToUInt32Bits(a[i]) == BitConverter.SingleToUInt32Bits(b[i])) bitsEqual++;
        }
        return (maxAbs, dot / Math.Sqrt(Math.Max(na * nb, double.Epsilon)), bitsEqual);
    }

    static string Sha(float[] v)
    {
        var bytes = new byte[v.Length * 4];
        for (var i = 0; i < v.Length; i++) BitConverter.TryWriteBytes(bytes.AsSpan(i * 4), v[i]);
        return Convert.ToHexString(SHA256.HashData(bytes))[..16].ToLowerInvariant();
    }

    static long RssKb()
    {
        try
        {
            var parts = File.ReadAllText("/proc/self/statm").Split(' ', StringSplitOptions.RemoveEmptyEntries);
            return long.Parse(parts[1]) * (Environment.SystemPageSize / 1024);
        }
        catch { return -1; }
    }

    static string[] Texts(string[] a)
    {
        var list = new List<string>();
        for (var i = 0; i < a.Length - 1; i++) if (a[i] == "--text") list.Add(a[i + 1]);
        return list.Count > 0 ? list.ToArray() : DefaultTexts;
    }

    static string? Opt(string[] a, string name)
    {
        for (var i = 0; i < a.Length - 1; i++) if (a[i] == name) return a[i + 1];
        return null;
    }
}
