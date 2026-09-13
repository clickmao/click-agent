using System.Text.Json;
using Xunit;
using agent.rover.infer;
using agent.rover.runtime;

namespace agent.tests;

/// <summary>
/// R403 · RoPE 配对约定 —— 静默错误的高危点 (用错不抛错, 只让位置信息错乱)。
///
/// 权威源: llama.cpp <c>llama_model_rope_type()</c>; 机械提取存档 <c>eval/rover/oracle/rope-types.json</c>。
/// 断言全部绑定真实行为, 并配反向控制:
///  ① 金标向量: 两种约定各自与**独立算法**算出的期望值逐分量一致 (期望值由 ggml 内核公式在测试外计算后硬编码);
///  ② 同约定对账: RopeTable (预计算表) 与 CpuKernels.Rope (直接算) 在同一约定下必须一致;
///  ③ 负控: 两种约定的结果必须显著不同 —— 否则"配对参数被忽略"会空心通过;
///  ④ 频率表与约定无关: 只有取数下标变; 防"顺手改了角度"的隐性改动;
///  ⑤ 存档对账: 全部 NORM/NEOX arch 的 FromArch 判定与 llama.cpp 原表逐项一致。
/// </summary>
public class RoverRopeTests
{
    private const float RopeBase = 10000f;
    private const int HeadDim = 8;
    private const int Pos = 3;

    // 独立算法 (ggml 内核公式) 在测试外算出的期望值: head_dim=8, n_rot=8, pos=3, base=10000, x=[1..8]
    //   theta_j = pos * base^(-2j/8); NEOX 配对 (j, j+4); NORM 配对 (2j, 2j+1)
    private static readonly float[] GoldenNeox = [-1.695593f, 0.137552f, 2.788682f, 3.975982f, -4.808842f, 6.323059f, 7.086837f, 8.011964f];
    private static readonly float[] GoldenNorm = [-1.272233f, -1.838865f, 1.683929f, 4.707907f, 4.817777f, 6.147278f, 6.975969f, 8.020964f];

    private static float[] UnitVec()
    {
        var x = new float[HeadDim];
        for (int i = 0; i < HeadDim; i++) x[i] = i + 1;
        return x;
    }

    private static float[] Apply(RopePairing pairing, float[] input, int pos = Pos)
    {
        var v = (float[])input.Clone();
        new RopeTable(HeadDim, RopeBase, "none", 0f, Math.Max(pos + 1, 32), pairing).Apply(v, 1, HeadDim, pos);
        return v;
    }

    private static void AssertClose(float[] expected, float[] actual, float tol = 1e-4f)
    {
        Assert.Equal(expected.Length, actual.Length);
        for (int i = 0; i < expected.Length; i++)
            Assert.True(Math.Abs(expected[i] - actual[i]) <= tol,
                $"第 {i} 维不符: expected={expected[i]} actual={actual[i]} diff={Math.Abs(expected[i] - actual[i])} pairing_impl");
    }

    [Fact]
    public void NeoxHalf_MatchesIndependentGoldenVector()
        => AssertClose(GoldenNeox, Apply(RopePairing.NeoxHalf, UnitVec()));

    [Fact]
    public void NormConsecutive_MatchesIndependentGoldenVector()
        => AssertClose(GoldenNorm, Apply(RopePairing.NormConsecutive, UnitVec()));

    /// <summary>负控: 若两个配对给出相同结果, 说明配对分支没有真正生效 (空心)。</summary>
    [Fact]
    public void Pairings_MustBeDistinct_NegativeControl()
    {
        var a = Apply(RopePairing.NormConsecutive, UnitVec());
        var b = Apply(RopePairing.NeoxHalf, UnitVec());
        float md = 0;
        for (int i = 0; i < a.Length; i++) md = Math.Max(md, Math.Abs(a[i] - b[i]));
        Assert.True(md > 0.1f, $"两种配对结果几乎相同 (max_abs_diff={md}) ⇒ 配对参数未生效");
    }

    /// <summary>同一约定下: 预计算表实现 == 直接内核实现 (两者独立编码, 不是同一条代码路径)。</summary>
    [Theory]
    [InlineData(RopePairing.NormConsecutive)]
    [InlineData(RopePairing.NeoxHalf)]
    public void Table_And_DirectKernel_Agree(RopePairing pairing)
    {
        const int heads = 3, dim = 8, pos = 5;
        var seed = new float[heads * dim];
        for (int i = 0; i < seed.Length; i++) seed[i] = (float)Math.Sin(i * 0.017) * 1.5f + 0.25f;

        var t = (float[])seed.Clone();
        new RopeTable(dim, RopeBase, "none", 0f, pos + 1, pairing).Apply(t, heads, dim, pos);
        var k = (float[])seed.Clone();
        CpuKernels.Rope(k, heads, dim, pos, RopeBase, 4096, 0f, 0f, 0f, pairing);

        float md = 0;
        for (int i = 0; i < t.Length; i++) md = Math.Max(md, Math.Abs(t[i] - k[i]));
        Assert.True(md < 1e-5f, $"pairing={pairing} 两实现不一致 max_abs_diff={md}");
    }

    /// <summary>频率表 (cos/sin 预计算) 与配对约定无关: 只有取数下标不同。</summary>
    [Fact]
    public void FrequencyTable_IsPairingIndependent()
    {
        var n = new RopeTable(HeadDim, RopeBase, "none", 0f, 32, RopePairing.NormConsecutive);
        var x = new RopeTable(HeadDim, RopeBase, "none", 0f, 32, RopePairing.NeoxHalf);
        Assert.Equal(n.PairCount, x.PairCount);
        for (int p = 0; p < 8; p++)
            for (int i = 0; i < n.PairCount; i++)
            {
                Assert.Equal(n.At(p, i).Cos, x.At(p, i).Cos);
                Assert.Equal(n.At(p, i).Sin, x.At(p, i).Sin);
            }
    }

    // ---------- ⑤ 与 Llama.cpp 原表 (存档资产) 逐项对账 ----------

    private static string Root
    {
        get
        {
            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "eval", "rover", "oracle", "rope-types.json")))
                dir = dir.Parent;
            return dir?.FullName ?? throw new InvalidOperationException("找不到仓库根 (eval/rover/oracle/rope-types.json)");
        }
    }

    [Fact]
    public void ArchMapping_MatchesVendoredLlamaCppTable()
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(Path.Combine(Root, "eval", "rover", "oracle", "rope-types.json")));
        var norm = doc.RootElement.GetProperty("norm").EnumerateArray().Select(e => e.GetString()!).ToList();
        var neox = doc.RootElement.GetProperty("neox").EnumerateArray().Select(e => e.GetString()!).ToList();

        Assert.True(norm.Count >= 40, $"存档 NORM arch 数偏少: {norm.Count}");
        Assert.True(neox.Count >= 60, $"存档 NEOX arch 数偏少: {neox.Count}");
        Assert.Contains("llama", norm);
        Assert.Contains("deepseek2", norm);
        Assert.Contains("qwen2", neox);
        Assert.Contains("qwen3", neox);

        foreach (var a in norm)
            Assert.True(RopePairings.FromArch(a) == RopePairing.NormConsecutive, $"arch={a} 应为 NORM");
        foreach (var a in neox)
            Assert.True(RopePairings.FromArch(a) == RopePairing.NeoxHalf, $"arch={a} 应为 NEOX");
        // 未收录 arch 与 llama.cpp 的 default 分支一致 ⇒ NEOX
        Assert.Equal(RopePairing.NeoxHalf, RopePairings.FromArch("some-unknown-arch"));
    }
}
