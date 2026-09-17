namespace agent.recall;


public sealed class RecallSourceDoc
{
    public required string Id { get; init; }
    public required string Path { get; init; }
    public required string Text { get; init; }
    public long Size { get; init; }
    public long MtimeTicks { get; init; }
    public long Inode { get; init; }
}
