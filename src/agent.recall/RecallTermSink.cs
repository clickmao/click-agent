namespace agent.recall;


internal sealed class RecallTermSink : ITokenSink
{
    private readonly Dictionary<ulong, RecallTermState> _terms;

    public RecallTermSink(Dictionary<ulong, RecallTermState> terms) => _terms = terms;

    public void AddToken(ReadOnlySpan<byte> utf8)
    {
        // 仅用于需要「裸 token 流」的诊断场景; 正常写段走 RecallPostingAccumulator.AddTokens。
        ulong h = RecallTokenizer.Hash(utf8);
        if (!_terms.ContainsKey(h))
        {
            _terms[h] = new RecallTermState { Term = utf8.ToArray() };
        }
    }
}
