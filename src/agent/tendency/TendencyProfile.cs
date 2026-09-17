namespace agent.tendency;


/// <summary>
/// 倾向配置
/// </summary>
public class TendencyProfile
{
    public string UserId { get; set; } = string.Empty;
    public Dictionary<string, double> TopicTendencies { get; set; } = new();
    public Dictionary<string, double> StyleTendencies { get; set; } = new();
    public string ComplexityTendency { get; set; } = "medium";
    public double Confidence { get; set; }
    public DateTime LastUpdated { get; set; } = DateTime.UtcNow;
    public int SampleSize { get; set; }
}
