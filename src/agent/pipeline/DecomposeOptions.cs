namespace agent.pipeline;


/// <summary>
/// 分解选项
/// </summary>
public class DecomposeOptions
{
    public int MaxSubTasks { get; set; } = 10;
    public long MaxTokensPerTask { get; set; } = 8000;
    public bool ParallelExecution { get; set; } = true;
}
