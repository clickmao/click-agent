namespace agent.recall;


public sealed class RecallHit
{
    public required int DocId { get; init; }
    public required string Segment { get; init; }
    public required double Score { get; init; }
    public required string Id { get; init; }
    public required string Path { get; init; }
    public required string Text { get; init; }

    /// <summary>产出物自带地址: 该文档正文里已存在的链接/文件地址 (召回沿地址走, 不靠分类)。</summary>
    public IReadOnlyList<string> Links { get; init; } = Array.Empty<string>();
}
