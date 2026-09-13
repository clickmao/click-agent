using Xunit;
using agent.embedcpu;
using agent.rover.gpu.spirv;

namespace agent.tests;

/// <summary>
/// R393 · 本地 BGE 的矩阵乘端口 + Vulkan 内核不变量 (设备无关机检)。
///
/// 覆盖三层:
///   ① 端口语义 —— CPU 端口 vs 独立朴素参考实现 (不共用被测代码路径);
///   ② 端口装配 —— 注入的端口确实被前向采纳 (不需要模型文件即可判);
///   ③ 内核不变量 —— 结构校验通过, 以及 lavapipe 实测逼出的形状约束
///      (循环头 OpLoopMerge 之后必须是无条件 OpBranch; 条件分支放回循环头会使
///       vkCreateComputePipelines 返回 VK_ERROR_UNKNOWN, 见 /tmp/r393probe 变体对账)。
///      该约束带负向控制组: 把好内核的循环头分支改成条件分支, 检查器必须报违规。
/// </summary>
public sealed class BgeMatMulPortTests
{
    // ── ① 端口语义 ───────────────────────────────────────────────────────────

    static float[] Rand(Random r, int n)
    {
        var a = new float[n];
        for (int i = 0; i < n; i++) a[i] = (float)(r.NextDouble() * 2 - 1);
        return a;
    }

    /// <summary>独立参考实现: y[t,o] = b[o] + Σ_k W[o,k]·x[t,k] (三重循环, 不用 SIMD)。</summary>
    static float[] Naive(float[] x, float[] w, float[] b, int seq, int inDim, int outDim)
    {
        var y = new float[seq * outDim];
        for (int t = 0; t < seq; t++)
            for (int o = 0; o < outDim; o++)
            {
                double acc = b[o];
                for (int k = 0; k < inDim; k++) acc += (double)w[o * inDim + k] * x[t * inDim + k];
                y[t * outDim + o] = (float)acc;
            }
        return y;
    }

    [Fact]
    public void CpuMatMulBackend_与朴素三重循环一致()
    {
        const int seq = 3, inDim = 4, outDim = 5;
        var r = new Random(393);
        var x = Rand(r, seq * inDim);
        var w = Rand(r, outDim * inDim);
        var b = Rand(r, outDim);

        var got = CpuMatMulBackend.Instance.MatMulAdd(x, w, b, seq, inDim, outDim);
        var want = Naive(x, w, b, seq, inDim, outDim);

        Assert.Equal(seq * outDim, got.Length);
        for (int i = 0; i < want.Length; i++) Assert.Equal(want[i], got[i], 5);
    }

    [Fact]
    public void CpuMatMulBackend_不改写入参()
    {
        var r = new Random(7);
        var x = Rand(r, 12); var w = Rand(r, 20); var b = Rand(r, 5);
        var xc = (float[])x.Clone(); var wc = (float[])w.Clone(); var bc = (float[])b.Clone();

        _ = CpuMatMulBackend.Instance.MatMulAdd(x, w, b, 3, 4, 5);

        Assert.Equal(xc, x); Assert.Equal(wc, w); Assert.Equal(bc, b);
    }

    [Fact]
    public void CpuMatMulBackend_端口名为cpu()
    {
        Assert.Equal("cpu", CpuMatMulBackend.Instance.Name);
        Assert.Same(CpuMatMulBackend.Instance, CpuMatMulBackend.Instance);
    }

    // ── ② 端口装配 ───────────────────────────────────────────────────────────

    [Fact]
    public void BgeEmbedder_采纳注入的端口()
    {
        // 不加载模型 (路径不存在) 也能判端口装配: 端口在构造期即确定
        using var a = new BgeCpuEmbedder("no-such-model.gguf", CpuMatMulBackend.Instance);
        using var b = new BgeCpuEmbedder("no-such-model.gguf");
        Assert.Equal("cpu", a.MatMulBackendName);
        Assert.Equal("cpu", b.MatMulBackendName);
        Assert.False(a.IsAvailable);
    }

    [Fact]
    public void BgeEmbedder_端口名为注入实现的名字()
    {
        using var e = new BgeCpuEmbedder("no-such-model.gguf", new NamedBackend("vulkan-stub"));
        Assert.Equal("vulkan-stub", e.MatMulBackendName);
    }

    sealed class NamedBackend(string name) : IMatMulBackend
    {
        public string Name { get; } = name;
        public float[] MatMulAdd(float[] input, float[] weight, float[] bias, int seq, int inDim, int outDim)
            => throw new NotSupportedException("stub");
    }

    // ── ③ 内核不变量 ─────────────────────────────────────────────────────────

    /// <summary>SPIR-V 指令扫描 (跳过 5 字头)。</summary>
    static List<(uint Op, int At, int Wc)> Instrs(uint[] w)
    {
        var list = new List<(uint, int, int)>();
        for (int i = 5; i < w.Length;)
        {
            uint wc = w[i] >> 16;
            if (wc == 0) break;
            list.Add((w[i] & 0xFFFFu, i, (int)wc));
            i += (int)wc;
        }
        return list;
    }

    /// <summary>违规计数: 循环头 (OpLoopMerge 所在块) 的收尾指令必须是无条件 OpBranch。</summary>
    static int LoopHeadViolations(uint[] words)
    {
        var ins = Instrs(words);
        int bad = 0;
        for (int i = 0; i < ins.Count; i++)
        {
            if (ins[i].Op != Spv.OpLoopMerge) continue;
            if (i + 1 >= ins.Count || ins[i + 1].Op != Spv.OpBranch) bad++;
        }
        return bad;
    }

    [Fact]
    public void MatMulBias_结构校验通过且四绑定()
    {
        var k = Kernels.MatMulBias(512, 512);
        Assert.Equal(4, k.BufferCount);
        Assert.True(k.Words.Length > 0);
        Assert.Empty(SpirvValidator.Validate(k.Words, (int)k.LocalSizeX, k.BufferCount));
    }

    [Fact]
    public void MatMulBias_含唯一归约循环且循环头无条件分支()
    {
        var k = Kernels.MatMulBias(512, 512);
        var ins = Instrs(k.Words);

        Assert.Equal(1, ins.Count(x => x.Op == Spv.OpLoopMerge));
        Assert.Equal(1, ins.Count(x => x.Op == Spv.OpUDiv));      // 行号 = i / outDim
        Assert.Equal(1, ins.Count(x => x.Op == Spv.OpULessThan)); // 循环条件 k < inDim
        Assert.Contains(ins, x => x.Op == Spv.OpIAdd);            // 地址与计数 (可能多条)
        Assert.Equal(0, LoopHeadViolations(k.Words));              // lavapipe 实测约束
    }

    [Fact]
    public void MatMulBias_驱动约束检查器有判别力()
    {
        var k = Kernels.MatMulBias(64, 64);
        Assert.Equal(0, LoopHeadViolations(k.Words));               // 正向: 好内核 0 违规

        var bad = MutateLoopHeadToConditional(k.Words);
        Assert.Equal(1, LoopHeadViolations(bad));                   // 负向: 旧形状必被查出
    }

    [Fact]
    public void MatMulBias_形状特化()
    {
        var a = Kernels.MatMulBias(512, 512);
        var b = Kernels.MatMulBias(512, 2048);
        var c = Kernels.MatMulBias(512, 2048);

        Assert.Equal("matmul_bias_512x512", a.Name);
        Assert.Equal("matmul_bias_512x2048", b.Name);
        // 形状特化 = 常量值不同 ⇒ 字序列不同 (指令条数可能相同, 故不能比长度);
        // 同一形状必须逐字相同 —— 这是 PipeFor 按内核名+绑定数缓存的前提。
        Assert.False(a.Words.AsSpan().SequenceEqual(b.Words));
        Assert.True(b.Words.AsSpan().SequenceEqual(c.Words));
        Assert.Empty(SpirvValidator.Validate(b.Words, (int)b.LocalSizeX, b.BufferCount));
    }

    /// <summary>把循环头的 2 字 OpBranch 换成 4 字 OpBranchConditional (复现被驱动拒绝的旧形状)。</summary>
    static uint[] MutateLoopHeadToConditional(uint[] words)
    {
        var ins = Instrs(words);
        var head = ins.First(x => x.Op == Spv.OpLoopMerge);
        var branch = ins.First(x => x.At > head.At);
        Assert.Equal(Spv.OpBranch, branch.Op);
        Assert.Equal(2, branch.Wc);

        var merged = new List<uint>();
        merged.AddRange(words[..branch.At]);
        merged.Add(4u << 16 | Spv.OpBranchConditional);
        merged.Add(words[branch.At + 1]);   // 条件 id (结构检查不校验语义)
        merged.Add(words[branch.At + 1]);
        merged.Add(words[branch.At + 1]);
        merged.AddRange(words[(branch.At + branch.Wc)..]);
        return merged.ToArray();
    }
}
