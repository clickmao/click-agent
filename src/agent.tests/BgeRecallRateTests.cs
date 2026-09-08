using agent.rag;
using agent.llamalocal;
using Xunit;
using System.Text.Json;

namespace agentframework.tests;

/// <summary>
/// v0.13.3 B 期 — bge 语义档召回率真机测量 (长期观察任务②)。
/// 对照词袋兜底档 0.70: bge EmbeddingRouter 语义档应显著更高。
/// 需要真 bge 模型 (AGENTFRAMEWORK_BGE_MODEL); 缺失 → skip (诚实: 不假跑)。
/// </summary>
public class BgeRecallRateTests
{
    private readonly Xunit.Abstractions.ITestOutputHelper _out;
    public BgeRecallRateTests(Xunit.Abstractions.ITestOutputHelper o) => _out = o;
    private static (List<GtRecallDoc> docs, string repoRoot) Load()
    {
        var repoRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
        var docs = JsonSerializer.Deserialize<List<GtRecallDoc>>(
            File.ReadAllText(Path.Combine(repoRoot, "eval", "compression-audit-groundtruth.json")))!;
        return (docs, repoRoot);
    }

    private sealed record GtRecallDoc(
        [property: System.Text.Json.Serialization.JsonPropertyName("id")] string Id,
        [property: System.Text.Json.Serialization.JsonPropertyName("content")] string Content,
        [property: System.Text.Json.Serialization.JsonPropertyName("ground_truth")] Dictionary<string, string> GroundTruth);

    [Fact]
    public async Task Bge_Semantic_Recall_Measured_And_Reported()
    {
        var modelPath = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_BGE_MODEL");
        if (string.IsNullOrEmpty(modelPath) || !File.Exists(modelPath))
        {
            // 诚实 skip: bge 模型缺失时本测试不产数据 (不假跑) — CI 环境正常
            return;
        }
        var (docs, _) = Load();
        // 语义档查询 = 自然语言问句 (非关键词堆叠 — 与词袋档区分, 语义泛化才是 bge 价值):
        var queries = docs.Take(20).Select(d =>
        {
            var gt = d.GroundTruth;
            return $"{gt["entity_person"]}负责的{gt["entity_product"]}相关记录在哪篇文档里?";
        }).ToList();
        var expected = docs.Take(20).Select(d => d.Id).ToList();

        // bge 真机 embedding 直接算余弦 (绕过 RAGRecall 的 EmbeddingRouter 装配 — 更精确隔离 bge 档):
        using var embedder = new BgeEmbedder(modelPath);
        // 真缺陷 69 (本测试发现): bge-q8 ctx=512 — 文档全文超窗 (500tok 样本实际 ~730 token)。
        // 语义档 embedding 输入必须截断至窗口内 (与生产 RAG chunking 语义一致); 超窗异常即真机词袋回退的证据。
        var maxChars = 440; // ~440 汉字 ≈ 460 tok < 512 (安全边距)
        var docEmbeddings = new List<float[]>();
        foreach (var d in docs.Take(20))
            docEmbeddings.Add(await embedder.EmbedAsync(d.Content.Length > maxChars ? d.Content[..maxChars] : d.Content, CancellationToken.None));
        var queryEmbeddings = new List<float[]>();
        foreach (var q in queries)
            queryEmbeddings.Add(await embedder.EmbedAsync(q, CancellationToken.None));

        int hit5 = 0, hit1 = 0, qn = 0; double mrr = 0;
        // R252 真修: 原写法 for(i<qn) 且 qn 在循环内递增 — qn 恒 0, 循环零迭代 (自引用假阴性)。
        for (var i = 0; i < queryEmbeddings.Count; i++)
        {
            var scored = docEmbeddings
                .Select((de, di) => (di, Cos(queryEmbeddings[i], de)))
                .OrderByDescending(x => x.Item2)
                .Take(5)
                .ToList();
            var rank = scored.FindIndex(x => expected[x.di] == expected[i]) + 1;
            qn++;
            if (rank > 0) { hit5++; mrr += 1.0 / rank; if (rank == 1) hit1++; }
        }
        var rate = qn > 0 ? (double)hit5 / qn : 0.0;
        _out.WriteLine($"BGE_SEMANTIC_RECALL Recall@5={rate:F2} ({hit5}/{qn}) Hit@1={hit1} MRR={mrr / Math.Max(1, qn):F3}");
        // 观察: 打印数据 (长期观察任务数据源), 断言 = bge 档不应低于词袋档 0.70 (否则语义档无价值 → 底座靶点):
        Assert.True(rate >= 0.70, $"bge 语义档 Recall@5={rate:F2} ({hit5}/{qn}) 低于词袋档 0.70 — 语义检索无增益, 底座靶点");
    }

    private static double Cos(float[] a, float[] b)
    {
        double dot = 0, na = 0, nb = 0;
        for (var i = 0; i < a.Length; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
        return na == 0 || nb == 0 ? 0 : dot / (Math.Sqrt(na) * Math.Sqrt(nb));
    }
}
