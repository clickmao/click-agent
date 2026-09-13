using Xunit;
using agent.rover.infer;

namespace agent.tests;

/// <summary>
/// R400 · 确定性采样器测试。
/// 断言绑定真实行为: ① 随机源与独立 Python 实现的参考向量逐位一致 (跨实现对账);
/// ② 确定性 (同 seed 同序列) 与敏感性 (异 seed 可分辨); ③ 温度/top-k/top-p 的边界语义;
/// ④ 反向控制: 采样不得退化为恒 argmax (否则"采样"是空心的); ⑤ id 恒在词表内。
/// </summary>
public class RoverSamplerTests
{
    [Fact]
    public void SplitMix64_MatchesReferenceVector()
    {
        ulong[] got = Sampler.SplitMix64Vector(12345, Sampler.ReferenceVector.Length);
        Assert.Equal(Sampler.ReferenceVector, got);

        // 参考向量自身必须非常数序列 (防止把常量表写死成同值自证)
        Assert.True(Sampler.ReferenceVector.Distinct().Count() == Sampler.ReferenceVector.Length);
    }

    [Fact]
    public void ArgMax_TiesPickLowestId_And_ZeroTemperatureIsGreedy()
    {
        float[] logits = [0.1f, 5.0f, 5.0f, -1.0f];
        Assert.Equal(1, Sampler.ArgMax(logits));

        Sampler s = new(new SamplerOptions(Temperature: 0f, TopK: 40, TopP: 0.95f, Seed: 7));
        for (int i = 0; i < 20; i++)
        {
            Assert.Equal(1, s.Next(logits));
        }

        Assert.Equal(0L, s.Draws); // 贪心路径不消耗随机数
    }

    [Fact]
    public void SameSeed_SameSequence_DifferentSeed_Diverges()
    {
        float[] logits = Build(64, 3);
        List<int> Seq(ulong seed)
        {
            Sampler s = new(new SamplerOptions(0.9f, 40, 0.95f, seed));
            List<int> outp = [];
            for (int i = 0; i < 40; i++)
            {
                outp.Add(s.Next(logits));
            }

            return outp;
        }

        Assert.Equal(Seq(12345), Seq(12345));
        Assert.NotEqual(Seq(12345), Seq(999));
    }

    [Fact]
    public void TopK1_IsAlwaysArgMax()
    {
        float[] logits = Build(128, 5);
        int want = Sampler.ArgMax(logits);
        Sampler s = new(new SamplerOptions(1.5f, 1, 1.0f, 42));
        for (int i = 0; i < 30; i++)
        {
            Assert.Equal(want, s.Next(logits));
        }
    }

    [Fact]
    public void TopP_RestrictsToNucleus()
    {
        // 峰值分布: id 7 概率占绝对多数, top-p=0.5 应只落在前两个候选内
        float[] logits = new float[256];
        Array.Fill(logits, -20f);
        logits[7] = 10f;
        logits[9] = 9f;
        Sampler s = new(new SamplerOptions(1.0f, 0, 0.5f, 2026));
        for (int i = 0; i < 100; i++)
        {
            int id = s.Next(logits);
            Assert.Contains(id, new[] { 7, 9 });
        }
    }

    [Fact]
    public void Sampling_IsNotDegenerateArgMax()
    {
        // 反向控制: 平坦分布 + 高温下必须出现多个不同 id (否则采样器其实是贪心)
        float[] logits = new float[512];
        Array.Fill(logits, 1f);
        Sampler s = new(new SamplerOptions(2.0f, 0, 1.0f, 31337));
        HashSet<int> seen = [];
        for (int i = 0; i < 300; i++)
        {
            seen.Add(s.Next(logits));
        }

        Assert.True(seen.Count > 5, $"平坦分布仅采样到 {seen.Count} 个不同 id ⇒ 采样退化");
        Assert.Equal(300L, s.Draws);
    }

    [Fact]
    public void SampledIds_AlwaysInVocab()
    {
        float[] logits = Build(4096, 11);
        Sampler s = new(new SamplerOptions(3.0f, 250, 0.98f, 5));
        for (int i = 0; i < 200; i++)
        {
            int id = s.Next(logits);
            Assert.InRange(id, 0, logits.Length - 1);
        }
    }

    [Fact]
    public void TopK_AboveVocab_IsClamped()
    {
        float[] logits = Build(8, 17);
        Sampler s = new(new SamplerOptions(1.0f, 1000, 1.0f, 3));
        for (int i = 0; i < 50; i++)
        {
            Assert.InRange(s.Next(logits), 0, 7);
        }
    }

    [Fact]
    public void EmptyLogits_Throws()
    {
        Sampler s = new(new SamplerOptions());
        Assert.Throws<ArgumentException>(() => s.Next(ReadOnlySpan<float>.Empty));
    }

    private static float[] Build(int n, int seed)
    {
        // 确定性可分辨的 logits (不依赖 System.Random 实现细节)
        float[] v = new float[n];
        for (int i = 0; i < n; i++)
        {
            v[i] = (float)(Math.Sin((i + 1) * seed * 0.37) * 4.0);
        }

        return v;
    }
}
