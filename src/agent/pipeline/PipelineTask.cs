namespace agent.pipeline;

/// <summary>
/// 管道任务
/// </summary>
public class PipelineTask
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Name { get; set; } = string.Empty;
    public string Input { get; set; } = string.Empty;
    public core.TaskType Type { get; set; } = core.TaskType.General;
    public core.TaskStatus Status { get; set; } = core.TaskStatus.Pending;
    public string? Result { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? StartedAt { get; set; }
    public DateTime? CompletedAt { get; set; }
    public double Progress { get; set; }
}
