namespace agent.exploration;


public sealed class ThinkMemoryHit
{
    public ThinkRecord Record { get; set; } = new();
    public double Similarity { get; set; }
    /// <summary>命中后前置的优先阅览链接 (按历史置信降序)</summary>
    public List<string> PreferredRefs { get; set; } = new();
}
