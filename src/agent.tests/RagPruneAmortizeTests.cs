using Xunit;
using agent.rag;
using Microsoft.Extensions.Logging.Abstractions;

/// <summary>
/// v0.16.3 (R331, P12): RAG 落盘裁剪摊销 — PersistDocument 原每 append 无条件整读判 512 行裁剪
/// (过上限后每消息 O(库大小) 文件 IO); 改为内存计数每 64 次追加整读一次。
/// 锁定契约: 文件行数有界 (512+63), 裁剪保留最新, 读侧 (重启恢复) 兼容, 小库不裁剪。
/// </summary>
public class RagPruneAmortizeTests
{
    private static (RAGRecall Recall, string Path) Create()
    {
        // 隔离落盘路径 (R81 评测隔离原则)
        var tmp = Path.Combine(Path.GetTempPath(), "rag-prune-amortize", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tmp);
        var path = Path.Combine(tmp, "index.jsonl");
        var recall = new RAGRecall(
            NullLogger<RAGRecall>.Instance,
            new RAGConfig { EmbeddingDimension = 128, EnableHybridSearch = true, PersistPathOverride = path });
        return (recall, path);
    }

    private static RAGDocument Doc(int i) => new RAGDocument
    {
        Id = $"doc-{i}",
        Content = $"第 {i} 号独特记忆内容: RAG 裁剪摊销验证, 编号 {i}。",
        DocumentType = "conversation",
    };

    [Fact]
    public async Task ManyDocuments_FileBoundedByCapPlusSlack_KeepsNewest()
    {
        var (recall, path) = Create();
        const int total = 700; // 512+63=575 上界内, 必跨多次裁剪检查 (64 间隔)
        for (int i = 1; i <= total; i++)
            await recall.IndexAsync(Doc(i));

        var lines = File.ReadAllLines(path);
        // 有界松弛: 裁剪检查在 64 次追加边界, 文件可在 512..575 之间
        Assert.InRange(lines.Length, 513, 575);
        // 裁剪保留最新 — 最新 doc-700 必在, 最老 doc-1 必已裁掉 (文件侧)
        Assert.Contains(lines, l => l.Contains("\"doc-700\""));
        Assert.DoesNotContain(lines, l => l.Contains("\"doc-1\""));
        // 内存 _documents 不受文件裁剪影响 (700 全在 — 文件仅重启恢复用)
        Assert.NotNull(await recall.GetAsync("doc-700"));
        Assert.NotNull(await recall.GetAsync("doc-1"));
    }

    [Fact]
    public async Task Reload_TrimmedFile_RestoresSurvivors_AndAppendContinues()
    {
        var (recall, path) = Create();
        for (int i = 1; i <= 700; i++)
            await recall.IndexAsync(Doc(i));

        // 新实例重载 (模拟重启): 恢复文件内幸存文档; 最老已裁, 最新在
        var reloaded = new RAGRecall(
            NullLogger<RAGRecall>.Instance,
            new RAGConfig { EmbeddingDimension = 128, EnableHybridSearch = true, PersistPathOverride = path });
        Assert.NotNull(await reloaded.GetAsync("doc-700"));
        Assert.Null(await reloaded.GetAsync("doc-1"));

        // 重载后继续追加仍正常 (计数从 0 起, 无残留裁剪状态)
        await reloaded.IndexAsync(Doc(701));
        var lines = File.ReadAllLines(path);
        Assert.Contains(lines, l => l.Contains("\"doc-701\""));
    }

    [Fact]
    public async Task SmallCorpus_NoPrematureTrim()
    {
        var (recall, path) = Create();
        for (int i = 1; i <= 50; i++) // < 64: 从未到裁剪检查边界
            await recall.IndexAsync(Doc(i));

        var lines = File.ReadAllLines(path);
        Assert.Equal(50, lines.Length); // 一文档一行, 零裁剪
        Assert.Contains(lines, l => l.Contains("\"doc-1\""));
    }
}
