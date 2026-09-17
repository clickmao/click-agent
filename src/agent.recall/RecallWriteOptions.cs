namespace agent.recall;


public sealed class RecallWriteOptions
{
    public RecallLinkOptions Links { get; init; } = RecallLinkOptions.Default;
    public int MaxDocsPerSegment { get; init; } = 20000;
    public long MaxPostingsBytesPerSegment { get; init; } = 48L * 1024 * 1024;
    public double K1 { get; init; } = RecallConstants.Bm25K1;
    public double B { get; init; } = RecallConstants.Bm25B;
    public RecallTokenizerOptions Tokenizer { get; init; } = RecallTokenizerOptions.Default;
}
