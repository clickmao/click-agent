using agent.vectormemory;
using Xunit;
using Xunit.Abstractions;

namespace agentframework.tests;

/// <summary>
/// v0.16.1 R329 (T-B4): HashEmbeddingProvider 双实现统一 — vectormemory 升级为唯一实现
/// (dim 384, RAGConfig.Tokenize 同族分词: ASCII 标点切 + ascii↔非ascii 边界切 R44 + 中文 2-gram R6),
/// llamalocal 256 版退役。锁定: 维度统一 / 中文与中英混写分词召回 / EmbeddingRouter fallback 指向统一版。
/// </summary>
public class HashEmbeddingUnificationTests
{
    private readonly ITestOutputHelper _out;
    public HashEmbeddingUnificationTests(ITestOutputHelper o) => _out = o;

    private static float[] Embed(string text, int dim = 384)
    {
        return new HashEmbeddingProvider(dim).Embed(text);
    }

    private static double Cos(float[] a, float[] b)
    {
        double dot = 0, na = 0, nb = 0;
        for (int i = 0; i < a.Length; i++)
        {
            dot += a[i] * b[i];
            na += a[i] * a[i];
            nb += b[i] * b[i];
        }
        var denom = System.Math.Sqrt(na) * System.Math.Sqrt(nb);
        return denom > 0 ? dot / denom : 0;
    }

    private static int NonZero(float[] v)
    {
        int n = 0;
        foreach (var x in v) if (x != 0) n++;
        return n;
    }

    [Fact]
    public void Unified_Dimension_384_And_Chinese_MultiBucket()
    {
        // T-B4: dim 统一 384 (旧 llamalocal 256 版退役); 中文标点句子分词生效 (多桶非 1 桶)
        var v = Embed("rust 的所有权机制。测试文本");
        Assert.Equal(384, v.Length);
        Assert.True(NonZero(v) >= 8, $"中文分词应产生多桶 (实际 {NonZero(v)})");
    }

    [Fact]
    public void R44_MixedScript_Segmentation_Recalls()
    {
        // R44 中英混写黏连: "rust的所有权" (无空格) 与 "rust 的所有权 概念" 共享分词 → 高相似;
        // 与无关文本区分 (判别力)。
        var q = Embed("rust的所有权");
        var hit = Embed("rust 的所有权 概念 详解");
        var miss = Embed("今天天气不错适合出去散步");
        var simHit = Cos(q, hit);
        var simMiss = Cos(q, miss);
        _out.WriteLine($"simHit={simHit:F3} simMiss={simMiss:F3}");
        Assert.True(simHit > simMiss, $"混写切分召回应优于无关文本 (hit={simHit:F3} miss={simMiss:F3})");
        Assert.True(simHit > 0.05, $"hit 相似度过低: {simHit:F3}");
    }

    [Fact]
    public void R6_Chinese_NoSpace_Still_Recalls()
    {
        // R6: 中文整句无分隔 → 2-gram 滑窗保证同句子片段共享 token
        var q = Embed("所有权机制");
        var hit = Embed("Rust 的所有权机制讲解");
        var miss = Embed("异步编程模型与并发原语");
        Assert.True(Cos(q, hit) > Cos(q, miss), "2-gram 滑窗应让同片段召回优于无关文本");
    }

    [Fact]
    public void English_Word_Segmentation_Not_Regressed()
    {
        // 旧 vectormemory 版英文整词语义不回退 (R100 行为面)
        var q = Embed("memory leak");
        var hit = Embed("memory leak detection in rust");
        var miss = Embed("股票市场波动分析");
        Assert.True(Cos(q, hit) > Cos(q, miss), "英文整词召回不应回退");
    }

    [Fact]
    public void EmbeddingRouter_Fallback_Uses_Unified_384()
    {
        // R352: EmbeddingRouter 语义档注入 null (无 llm-service) → HashEmbeddingProvider 兜底 (384, name=hash)
        var router = new agent.llamalocal.EmbeddingRouter(null);
        Assert.Equal(384, router.Dimension);
        Assert.Equal("hash", router.Name);
        var v = router.Embed("rust 的所有权机制。测试文本");
        Assert.Equal(384, v.Length);
        Assert.True(NonZero(v) >= 8, $"fallback 分词应产生多桶 (实际 {NonZero(v)})");
    }
}
