namespace agent.recall;


public sealed class RecallFileEntry
{
    public required string RelativePath { get; init; }
    public required long Size { get; init; }
    public required long MtimeTicks { get; init; }
}
