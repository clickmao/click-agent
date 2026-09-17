namespace agent.recall;


/// <summary>BM25 参数 + 打分口径。</summary>
public sealed class RecallScoringOptions
{
    public double K1 { get; init; } = 1.2;
    public double B { get; init; } = 0.75;
    public double DocFreqIdf(int docCount, int docFreq)
        => Math.Log(1.0 + (docCount - docFreq + 0.5) / (docFreq + 0.5));

    public double Score(double idf, int tf, int docLen, double avgDocLen)
    {
        double dl = docLen < 1 ? 1 : docLen;
        double norm = 1.0 - B + B * (dl / Math.Max(1.0, avgDocLen));
        return idf * tf * (K1 + 1.0) / (tf + K1 * norm);
    }

    public double UpperBound(double idf, int maxTf, double avgDocLen)
    {
        double norm = 1.0 - B + B * (1.0 / Math.Max(1.0, avgDocLen));
        return idf * maxTf * (K1 + 1.0) / (maxTf + K1 * norm);
    }
}
