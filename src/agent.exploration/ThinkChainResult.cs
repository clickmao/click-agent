namespace agent.exploration;


public sealed class ThinkChainResult
{
    public ConvergeReason Reason { get; set; }
    public int Steps { get; set; }
    public int SourcesUsed { get; set; }
    public double AvgConfidence { get; set; }
    public int WallMs { get; set; }
    public List<ExploreStepResult> Trail { get; set; } = new();
}
