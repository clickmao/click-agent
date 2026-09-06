using Xunit;
using System.Linq;
using agent.rag;

/// <summary>
/// v0.11.0 R109 (fix#41): RAG 同内容写入去重 —
/// 千轮循环场景同题记忆反复入库, 召回 rel 并列退化、同题召回 token 随库线性涨
/// (实测 C11 Memory 126→465tok, 2snip rel 同 0.45)。
/// 修复: IndexAsync 归一化内容指纹 (小写/压空白, FNV-1a 64bit 零反射) 命中 → 复用既有 Id。
/// </summary>
public class RagDedupTests
{
    private static RAGRecall Create()
    {
        // 隔离落盘路径 (R81 评测隔离原则): 防仓库根 data/rag/index.jsonl 历史记忆污染断言
        var tmp = Path.Combine(Path.GetTempPath(), "rag-dedup-test", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tmp);
        return new RAGRecall(
            Microsoft.Extensions.Logging.Abstractions.NullLogger<RAGRecall>.Instance,
            new RAGConfig { EmbeddingDimension = 128, EnableHybridSearch = true, PersistPathOverride = Path.Combine(tmp, "index.jsonl") });
    }

    [Fact]
    public async Task SameContent_ReusesDocumentId()
    {
        var recall = Create();
        var doc1 = new RAGDocument { Content = "项目代号是 Omega 队伍，负责千轮评测。", DocumentType = "conversation" };
        var doc2 = new RAGDocument { Content = "项目代号是  Omega 队伍，负责千轮评测!", DocumentType = "conversation" }; // 空白/标点差异
        await recall.IndexAsync(doc1);
        await recall.IndexAsync(doc2);
        Assert.Equal(doc1.Id, doc2.Id);
    }

    [Fact]
    public async Task DifferentContent_GetsDistinctIds()
    {
        var recall = Create();
        var doc1 = new RAGDocument { Content = "项目代号是 Omega 队伍。", DocumentType = "conversation" };
        var doc2 = new RAGDocument { Content = "完全不同的另一条记忆内容, 讨论数据库索引结构。", DocumentType = "conversation" };
        await recall.IndexAsync(doc1);
        await recall.IndexAsync(doc2);
        Assert.NotEqual(doc1.Id, doc2.Id);
    }

    [Fact]
    public async Task Reindex_SameContent_CorpusDoesNotGrow()
    {
        var recall = Create();
        for (int i = 0; i < 5; i++)
            await recall.IndexAsync(new RAGDocument { Content = "千轮评测循环 guard 说明: 每批 5 用例全绿后继续。", DocumentType = "conversation" });
        var results = await recall.RecallAsync(new RecallRequest
        {
            Query = "千轮评测循环 guard", TopK = 10, MinScore = 0.3,
        });
        var distinct = results.Select(r => r.Document.Id).Distinct().Count();
        Assert.Equal(1, distinct);
    }
}
