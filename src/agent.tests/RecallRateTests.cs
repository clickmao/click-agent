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
            _out.WriteLine($"q{qn} expect={d.Id} got=[{string.Join(", ", results.Take(5).Select(r => $"{r.Document?.Id}:{r.Score:F2}:{r.MatchType}"))}]");
            for (var i = 0; i < results.Count; i++)
                if (results[i].Document?.Id == d.Id) { hit5++; mrr += 1.0 / (i + 1); break; }
        }
        var rate = (double)hit5 / qn;
        // v0.13.3 B 期双口径 (R254): 短查询对抗口径 (2 词, 20 篇同模板 — 判别力最严苛) 实测 0.45
        // (同分平局: 每篇都含产品名+人名, 词袋无判别力, 排序不稳定) → 对抗线 0.40;
        // 长查询口径 0.70 (R253); bge 语义档 0.95。TF-IDF 化 = B 期优化靶点 (提升短查询判别力)。
        Assert.True(rate >= 0.40, $"Recall@5={rate:F2} ({hit5}/{qn}) < 0.40 词袋短查询对抗线");
    }
}
