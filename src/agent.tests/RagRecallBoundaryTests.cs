using Xunit;
using System.Linq;
using agent.rag;

/// <summary>
/// v0.11.0 R44 (真缺陷 27): 中英混写黏连 token + 词袋 embedding 长文稀释 —
/// 查询词 ("Rust") 命中文档却因总分 0.291 < 0.3 被砍。
/// 修复: Tokenize 中英边界切分 + 内容命中相关性下限 0.45。
/// </summary>
public class RagRecallBoundaryTests
{
    [Fact]
    public async Task Mixed_CJK_Ascii_Query_Recalls_Doc()
    {
        var recall = new RAGRecall(Microsoft.Extensions.Logging.Abstractions.NullLogger<RAGRecall>.Instance,
            new RAGConfig { EmbeddingDimension = 128, EnableHybridSearch = true });
        await recall.IndexAsync(new RAGDocument
        {
            Id = "1", Content = "Q: 记住我最喜欢的语言是Rust\nA: 好的，已记住。",
            DocumentType = "conversation",
        });
        var results = await recall.RecallAsync(new RecallRequest
        {
            Query = "Rust的所有权机制是什么", TopK = 10, MinScore = 0.3,
        });
        var scores = string.Join(",", results.Select(r => r.Score.ToString("F3")));
        Assert.True(results.Count > 0, $"scores=[{scores}]");
        Assert.True(double.Parse(scores.Split(',')[0]) >= 0.3, $"score too low: {scores}");
    }
}
