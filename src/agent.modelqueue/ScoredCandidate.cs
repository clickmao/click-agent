namespace agent.modelqueue;


/// <summary>选模打分结果 (审计/调试 — LastSelectionBasis 落此)</summary>
public sealed class ScoredCandidate
{
    public ModelCatalogEntry Model { get; init; } = null!;
    public double TotalScore { get; init; }
    public double PriceScore { get; init; }
    public double SpeedScore { get; init; }
    public double ReasoningScore { get; init; }
}
