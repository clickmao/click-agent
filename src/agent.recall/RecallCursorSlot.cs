namespace agent.recall;


internal sealed class RecallCursorSlot
{
    public required RecallPostingCursor Cursor { get; init; }
    public required double UpperBound { get; init; }
    public required double Idf { get; init; }
    public required int QueryTf { get; init; }
}
