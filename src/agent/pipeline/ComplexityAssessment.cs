namespace agent.pipeline;


/// <summary>
/// 复杂度评估
/// </summary>
public class ComplexityAssessment
{
    public core.TaskType Type { get; set; }
    public int ComplexityLevel { get; set; } // 1-5
    public List<string> RequiredCapabilities { get; set; } = new();
    public long EstimatedTokens { get; set; }
    public TimeSpan EstimatedTime { get; set; }
    public List<string> Risks { get; set; } = new();
}
