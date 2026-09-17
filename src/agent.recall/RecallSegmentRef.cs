namespace agent.recall;


public sealed class RecallSegmentRef
{
    public required string Name { get; init; }
    public required int DocCount { get; init; }
    public int TombstoneCount { get; set; }
}
