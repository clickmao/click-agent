namespace agent.pipeline;


/// <summary>
/// 管道上下文
/// </summary>
public class PipelineContext
{
    public string SessionId { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public Dictionary<string, object> Data { get; set; } = new();
    public List<PipelineTask> Tasks { get; set; } = new();
    public Dictionary<string, string> Results { get; set; } = new();
}
