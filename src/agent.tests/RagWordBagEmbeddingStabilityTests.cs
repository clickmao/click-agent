using Xunit;
using agent.rag;
using Microsoft.Extensions.Logging.Abstractions;

/// <summary>
/// R422 附带修复: 词袋 embedding 的**哈希/下标契约**。
/// 原缺陷 (真机全量/隔离跑各红 2 例, 随后 6 连跑全绿 ⇒ 概率性 ~20%/进程):
///   ① `Math.Abs(word.GetHashCode())` —— .NET 的 string.GetHashCode() **进程随机化** ⇒ 同一文档跨进程向量不同
///      (落盘索引重启后不可复现), 且 `Math.Abs(int.MinValue)` 仍为负;
///   ② `(hash + seed * 31337) % dimension` —— 加法可**溢出为负** (hash 落在 int.MaxValue-62674 窗口) ⇒ 负下标崩溃。
/// 为什么判据不能只是"重跑变绿": 概率性失败 + 进程随机化 ⇒ 重跑不可判定。本测试把**失败等价类**
/// (溢出窗口内的 hash) 变成**确定性**断言, 并配负控 (旧公式在同一输入上确实产负下标)。
/// </summary>
public class RagWordBagEmbeddingStabilityTests
{
    /// <summary>旧实现等价式 (仅作负控, 不参与产品路径)。</summary>
    private static int OldFormulaBucket(int hash, int seed, int dimension)
        => (hash + seed * 31337) % dimension;

    /// <summary>测试侧**独立实现**的 FNV-1a (不调产品代码) —— 跨实现对账用。</summary>
    private static uint IndependentFnv1a(string s)
    {
        unchecked
        {
            var h = 2166136261u;
            foreach (var c in s)
            {
                h ^= c;
                h *= 16777619u;
            }
            return h;
        }
    }

    [Fact]
    public void NegativeControl_OldFormula_ProducesNegativeIndex_InOverflowWindow()
    {
        // hash 落在 int.MaxValue-62674 窗口内 ⇒ seed>=1 时 sum 溢出为负 (实测 seed=2 ⇒ -2147480975 % 128 = -15)
        var hash = int.MaxValue - 60000;
        var old = OldFormulaBucket(hash, 2, 128);
        Assert.True(old < 0, $"负控失效: 旧公式在该边界必须产负下标, 实测 {old}");

        // 正控 (修复后): 同一输入必落在 [0,128)
        var fixedIdx = RAGRecall.BucketOf(unchecked((uint)hash), 2, 128);
        Assert.InRange(fixedIdx, 0, 127);
    }

    [Fact]
    public void BucketOf_IsNonNegative_ForAdversarialHashes()
    {
        var inputs = new[] { 0u, 1u, 126u, 127u, 0x7fffffffu, 0x80000000u, 0xffffffffu, 0x7fff1a2bu };
        foreach (var h in inputs)
        {
            for (int seed = 0; seed < 3; seed++)
            {
                Assert.InRange(RAGRecall.BucketOf(h, seed, 128), 0, 127);
            }
        }
    }

    [Fact]
    public void StableHash_MatchesIndependentFnv1a_AndIsStable()
    {
        foreach (var s in new[] { "zzqone", "zzqtwo", "alpha", "拓扑序", "存在环", "a", "第 1 号独特记忆内容" })
        {
            Assert.Equal(IndependentFnv1a(s), RAGRecall.StableHash(s));
        }

        // 同输入恒同输出 (进程随机化的 GetHashCode 无法满足这条**跨进程**契约)
        Assert.Equal(RAGRecall.StableHash("zzqone"), RAGRecall.StableHash("zzqone"));
    }

    [Fact]
    public async Task WordBagVector_IsReproducible_AndRecallable()
    {
        // 端到端: 词袋档 (无 EmbeddingFunction) 索引 + 召回 —— 即旧实现负下标崩溃所走的路径
        var tmp = Path.Combine(Path.GetTempPath(), "rag-wordbag-stability", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tmp);
        var path = Path.Combine(tmp, "index.jsonl");

        var recall = new RAGRecall(
            NullLogger<RAGRecall>.Instance,
            new RAGConfig { EmbeddingDimension = 128, EnableHybridSearch = false, PersistPathOverride = path });

        await recall.IndexAsync(new RAGDocument
        {
            Id = "d1",
            Content = "zzqone zzqtwo 拓扑序 存在环",
            DocumentType = "conversation",
        });

        var hits = await recall.RecallAsync(new RecallRequest { Query = "zzqone zzqtwo", TopK = 3 });
        Assert.Contains(hits, h => h.Document.Id == "d1");
    }
}
