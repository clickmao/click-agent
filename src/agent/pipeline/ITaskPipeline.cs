namespace agent.pipeline;


/// <summary>
/// 任务管道接口
/// </summary>
public interface ITaskPipeline
{
    Task EnqueueAsync(PipelineTask task);
    Task<PipelineTask?> DequeueAsync(CancellationToken ct);
    Task CompleteAsync(string taskId, string result);
    Task FailAsync(string taskId, string error);
    IEnumerable<PipelineTask> GetPendingTasks();
    IEnumerable<PipelineTask> GetCompletedTasks();
}
