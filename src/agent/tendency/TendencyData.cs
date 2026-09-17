namespace agent.tendency;

/// <summary>
/// 倾向数据
/// </summary>
public class TendencyData
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string UserId { get; set; } = string.Empty;
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    public Dictionary<string, double> TopicScores { get; set; } = new();
    public Dictionary<string, double> StyleScores { get; set; } = new();
    public Dictionary<string, double> ComplexityPreferences { get; set; } = new();
    public string? PreferredResponseFormat { get; set; }
    public int ContextDepthPreference { get; set; } = 2; // 1-3
}
