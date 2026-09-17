namespace agent.exploration;


public sealed class StickyRouteDecision
{
    public bool Sticky { get; set; }
    public bool Avoid { get; set; }
    public string ModelId { get; set; } = string.Empty;
    public double Similarity { get; set; }
    public string Reason { get; set; } = string.Empty;
}
