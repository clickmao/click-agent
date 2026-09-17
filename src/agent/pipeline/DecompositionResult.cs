namespace agent.pipeline;


/// <summary>
/// 任务分解结果
/// </summary>
public class DecompositionResult
{
    public List<subagent.SubAgentTask> Tasks { get; set; } = new();
    public Dictionary<string, List<string>> Dependencies { get; set; } = new();
    public long EstimatedTotalTokens { get; set; }
    public TimeSpan EstimatedDuration { get; set; }
}
