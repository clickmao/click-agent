using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using agent.rag;
using Xunit;

namespace agent.tests;

/// <summary>
/// R572 上下文精排 KPI 单测 (用户钦定 2026-09-19)。断言面: ① 主指标 NDCG@k 与三件套算术逐位
/// 对上 IR 教材口径 (位次折扣 log2(i+1)); ② Recall@N 是前置天花板而非精排指标; ③ 精排段**只重排**
/// (输出集合 == 输入集合, 不扩召回) 且**确定** (同分按入参索引升序); ④ 词法基线在粗排倒挂时能抬 NDCG。
/// </summary>
public sealed class RerankMetricsTests
{
    [Fact]
    public void NdcgAtK_MatchesHandComputedIrFormula()
    {
        // gains=[2,1,0] 已是最优序 ⇒ NDCG@3 = 1
        var ideal3 = new List<int> { 2, 1, 0 };
        var idcg = 3.0 / Math.Log2(2) + 1.0 / Math.Log2(3);
        Assert.Equal(1.0, RerankMetrics.NdcgAtK(ideal3, 3), 9);
        Assert.Equal(idcg, RerankMetrics.Dcg(ideal3, 3), 9);

        // gains=[0,2,1]: DCG = 3/log2(3) + 1/log2(4); NDCG = DCG/IDCG
        var bad3 = new List<int> { 0, 2, 1 };
        var dcg = 3.0 / Math.Log2(3) + 1.0 / Math.Log2(4);
        Assert.Equal(dcg / idcg, RerankMetrics.NdcgAtK(bad3, 3), 9);

        // k 截断: 必需证据被挤出 top-2 ⇒ NDCG@2 明显低于 NDCG@3; IDCG@2 也按前两位理想序计算
        var idcg2 = 3.0 / Math.Log2(2) + 1.0 / Math.Log2(3);
        Assert.Equal((3.0 / Math.Log2(3)) / idcg2, RerankMetrics.NdcgAtK(bad3, 2), 9);

        // 全噪声 ⇒ 分母为 0 记 0 (不得 NaN)
        Assert.Equal(0.0, RerankMetrics.NdcgAtK(new List<int> { 0, 0 }, 2), 9);
    }

    [Fact]
    public void Mrr_And_Precision_And_Recall_FollowDefinitions()
    {
        Assert.Equal(0.5, RerankMetrics.Mrr(new List<int> { 0, 2, 1 }), 9);
        Assert.Equal(1.0 / 3.0, RerankMetrics.Mrr(new List<int> { 0, 0, 1 }), 9);
        Assert.Equal(0.0, RerankMetrics.Mrr(new List<int> { 0, 0, 0 }), 9);

        Assert.Equal(1.0, RerankMetrics.PrecisionAtK(new List<int> { 2, 1, 0 }, 2), 9);
        Assert.Equal(0.5, RerankMetrics.PrecisionAtK(new List<int> { 0, 2, 1 }, 2), 9);
        Assert.Equal(2.0 / 3.0, RerankMetrics.PrecisionAtK(new List<int> { 0, 2, 1 }, 3), 9);
        Assert.Equal(0.0, RerankMetrics.PrecisionAtK(new List<int> { 0, 2 }, 0), 9);

        // Recall@N = 前置天花板 (与位次无关): 3 条必需证据只召回 2 条 ⇒ 2/3
        Assert.Equal(2.0 / 3.0, RerankMetrics.RecallAtN(3, 2), 9);
        Assert.Equal(1.0, RerankMetrics.RecallAtN(0, 0), 9);
        Assert.Equal(1.0, RerankMetrics.RecallAtN(2, 5), 9);
    }

    [Fact]
    public void Measure_FlagsRecallShortfall_AndKeepsFourReadings()
    {
        var ok = RerankMetrics.Measure(new List<int> { 2, 1, 0 }, 3, requiredEvidence: 1, foundEvidence: 1);
        Assert.Equal("ok", ok.Status);
        Assert.Equal(3, ok.K);
        Assert.Contains("ndcg=", ok.Line(), StringComparison.Ordinal);

        var shortfall = RerankMetrics.Measure(new List<int> { 2, 0 }, 2, requiredEvidence: 2, foundEvidence: 1);
        Assert.Contains("召回不足", shortfall.Status, StringComparison.Ordinal);
        Assert.Equal(0.5, shortfall.RecallAtN, 9);
    }

    [Fact]
    public void RerankStage_IsOrderOnly_AndStable()
    {
        var pool = new List<RerankCandidate>
        {
            new("a", "same", 0.5),
            new("b", "same", 0.5),
            new("c", "same", 0.5),
        };
        var scorer = new LexicalRerankScorer(0.5);
        var ordered = RerankStage.Order(pool, "anything", scorer);

        // 不扩召回: 输出集合 == 输入集合 (元素与计数均不变)
        Assert.Equal(pool.Count, ordered.Length);
        var idsIn = new List<string>();
        foreach (var c in pool) idsIn.Add(c.Id);
        var idsOut = new List<string>();
        foreach (var c in ordered) idsOut.Add(c.Id);
        idsIn.Sort(StringComparer.Ordinal);
        idsOut.Sort(StringComparer.Ordinal);
        Assert.Equal(idsIn, idsOut);

        // 确定 + 稳定: 全同分时保持入参索引升序
        Assert.Equal(new[] { "a", "b", "c" }, new[] { ordered[0].Id, ordered[1].Id, ordered[2].Id });
    }

    [Fact]
    public async Task RerankStage_Engages_InLiveRecallPath()
    {
        // "有代码行 ≠ 生效": 必须经**真实召回路径**取到遥测非零, 否则该段是孤岛。
        var recall = new RAGRecall(
            Microsoft.Extensions.Logging.Abstractions.NullLogger<RAGRecall>.Instance,
            new RAGConfig { PersistPathOverride = Path.Combine(Path.GetTempPath(), $"rag-rr-{Guid.NewGuid():N}.jsonl") });
        await recall.IndexAsync(new RAGDocument { Id = "noise", Content = "zzzz yyyy xxxx" });
        await recall.IndexAsync(new RAGDocument { Id = "gold", Content = "sar sar sar" });

        var res = await recall.RecallAsync(new RecallRequest { Query = "sar", TopK = 5 });

        Assert.True(recall.RerankApplied > 0, "精排段未生效 (孤岛): 真实召回路径未触发 RerankApplied");
        Assert.True(res.Count >= 1, "召回本身返回空, 精排读数无从谈起");
        for (var i = 0; i < res.Count; i++) Assert.Equal(i + 1, res[i].Rank); // Rank 与精排后顺序一致
    }

    [Fact]
    public void LexicalRerank_LiftsNdcg_WhenCoarseOrderIsInverted()
    {
        // 粗排倒挂: 噪声 (coarse 0.9) 压住必需的 "sar" (coarse 0.1)
        var pool = new List<RerankCandidate>
        {
            new("noise", "zzzz", 0.9),
            new("gold", "sar", 0.1),
        };
        var gainsBefore = new List<int> { 0, 2 };
        var scorer = new LexicalRerankScorer(0.5);
        var ordered = RerankStage.Order(pool, "sar", scorer);

        Assert.Equal("gold", ordered[0].Id);          // 精排把必需证据顶到头部
        Assert.True(ordered[0].CoarseScore < ordered[1].CoarseScore); // 确实是"逆粗排"的结果

        var gainsAfter = new List<int> { 2, 0 };
        var before = RerankMetrics.NdcgAtK(gainsBefore, 2);
        var after = RerankMetrics.NdcgAtK(gainsAfter, 2);
        Assert.Equal(1.0, after, 9);
        Assert.True(after > before, $"精排未抬升 NDCG@2: before={before}, after={after}");
    }
}
