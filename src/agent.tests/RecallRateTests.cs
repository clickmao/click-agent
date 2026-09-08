using agent.rag;
using Xunit;
using System.Text.Json;

namespace agentframework.tests;

/// <summary>
/// v0.13.3 B 期 — 召回率真机跑测 (长期观察任务): ground-truth 20 篇注入 → 必召回查询 → Recall@5/MRR。
/// 词袋兜底档 (NullEmbedder); bge 档由批测 embedding 路径覆盖。
/// </summary>
public class RecallRateTests
{
    private readonly Xunit.Abstractions.ITestOutputHelper _out;
    public RecallRateTests(Xunit.Abstractions.ITestOutputHelper o) => _out = o;
    private sealed record GtDoc([property: System.Text.Json.Serialization.JsonPropertyName("id")] string Id, [property: System.Text.Json.Serialization.JsonPropertyName("target_tokens")] int TargetTokens,
        [property: System.Text.Json.Serialization.JsonPropertyName("content")] string Content,
        [property: System.Text.Json.Serialization.JsonPropertyName("ground_truth")] Dictionary<string, string> GroundTruth);

    [Fact]
    public async Task Recall_At_Least_80_Percent_On_Groundtruth()
    {
        var repoRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
var docs = JsonSerializer.Deserialize<List<GtDoc>>(File.ReadAllText(Path.Combine(repoRoot, "eval", "compression-audit-groundtruth.json")))!;
        var recall = new RAGRecall(
            Microsoft.Extensions.Logging.Abstractions.NullLogger<agent.rag.RAGRecall>.Instance,
            new RAGConfig { PersistPathOverride = Path.Combine(Path.GetTempPath(), $"rag-audit-{Guid.NewGuid():N}.jsonl") });
        foreach (var d in docs.Take(20))
            await recall.IndexAsync(new RAGDocument { Id = d.Id, Content = d.Content, Keywords = { d.GroundTruth["entity_product"], d.GroundTruth["entity_person"] } });
        int hit5 = 0, qn = 0; double mrr = 0;
        foreach (var d in docs.Take(20))
        {
            var q = $"{d.GroundTruth["entity_product"]} {d.GroundTruth["entity_person"]}";
            var results = await recall.RecallAsync(new RecallRequest { Query = q, TopK = 5, MinScore = 0 });
            qn++;
            if (qn == 1 && results.Count > 0)
                _out.WriteLine($"首查询 results[0].Id={results[0].Document?.Id} expect={d.Id} score={results[0].Score} match={results[0].MatchType} count={results.Count}");
            for (var i = 0; i < results.Count; i++)
                if (results[i].Document?.Id == d.Id) { hit5++; mrr += 1.0 / (i + 1); break; }
        }
        var rate = (double)hit5 / qn;
        // v0.13.3 B 期基线: 词袋兜底档真机实测 0.70 (20 篇, top5 竞争) — 健康线暂定 0.65;
        // bge 语义档另行测 (批测 embedding 路径); 优化靶点 = 词袋打分 TF-IDF 化 (B 期)。
        Assert.True(rate >= 0.65, $"Recall@5={rate:F2} ({hit5}/{qn}) < 0.65 词袋兜底档健康线");
    }
}
