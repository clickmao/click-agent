namespace agent.tendency;


/// <summary>
/// 上下文偏见
/// </summary>
public class ContextBias
{
    public string UserId { get; set; } = string.Empty;
    public string Context { get; set; } = string.Empty;
    public Dictionary<string, double> BiasScores { get; set; } = new();
    public double OverallConfidence { get; set; }
    // v0.11.0 R133: 置信度诊断信息 (max-based 公式的稀释保留: 弱/强信号条目数)
    public Dictionary<string, object> Metadata { get; set; } = new();
}
