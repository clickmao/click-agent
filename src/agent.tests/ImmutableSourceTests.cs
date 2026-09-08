using agent.rag;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.13.3 D5 — 原文恢复源声明 (工业模式 M2): 压缩产物只在 prompt 组装层,
/// RAG 源文档 = 不可变原文源; GetAsync(id) 任何时候可取回原文 (含多 chunk 文档的父文档)。
/// </summary>
public class ImmutableSourceTests
{
    [Fact]
    public async Task GetAsync_Returns_Original_Content_After_Compression()
    {
        // 压缩发生在 ContextAssembler 层 (snippet.CompressedContent), RAG 文档 Content 永不被覆盖:
        var recall = new RAGRecall(
            Microsoft.Extensions.Logging.Abstractions.NullLogger<agent.rag.RAGRecall>.Instance,
            new RAGConfig { PersistPathOverride = Path.Combine(Path.GetTempPath(), $"rag-imm-{Guid.NewGuid():N}.jsonl") });
        var original = "关键数字 8353 与签署人林晚秋的原始记录。" + new string('x', 600);
        await recall.IndexAsync(new RAGDocument { Id = "imm-1", Content = original });
        var doc = await recall.GetAsync("imm-1");
        Assert.NotNull(doc);
        // 原文未被截断/未变 (chunk 化只生成附带 chunk 文档, 父文档 Content 原样):
        Assert.Equal(original, doc!.Content);
        Assert.Contains("8353", doc.Content);
        Assert.Contains("林晚秋", doc.Content);
    }

    [Fact]
    public async Task Long_Doc_Chunked_Parent_Still_Has_Full_Content()
    {
        var recall = new RAGRecall(
            Microsoft.Extensions.Logging.Abstractions.NullLogger<agent.rag.RAGRecall>.Instance,
            new RAGConfig { PersistPathOverride = Path.Combine(Path.GetTempPath(), $"rag-imm2-{Guid.NewGuid():N}.jsonl") });
        var original = new string('N', 2000) + "尾部锚点END";
        await recall.IndexAsync(new RAGDocument { Id = "long-1", Content = original });
        var parent = await recall.GetAsync("long-1");
        Assert.NotNull(parent);
        Assert.Equal(original, parent!.Content); // 全文保留 (chunk 只是索引副本)
        var chunk = await recall.GetAsync("long-1#c1");
        Assert.NotNull(chunk); // chunk 可取 (向量召回副本)
    }
}
