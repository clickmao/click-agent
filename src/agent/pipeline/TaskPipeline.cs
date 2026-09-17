namespace agent.pipeline;


/// <summary>
/// 任务管道实现
/// </summary>
public class TaskPipeline : ITaskPipeline
{
    private readonly Queue<PipelineTask> _queue = new();
    private readonly Dictionary<string, PipelineTask> _tasks = new();
    private readonly object _lock = new();
    
    public Task EnqueueAsync(PipelineTask task)
    {
        lock (_lock)
        {
            _queue.Enqueue(task);
            _tasks[task.Id] = task;
        }
        return Task.CompletedTask;
    }
    
    public Task<PipelineTask?> DequeueAsync(CancellationToken ct)
    {
        lock (_lock)
        {
            if (_queue.TryDequeue(out var task))
            {
                task.StartedAt = DateTime.UtcNow;
                task.Status = core.TaskStatus.Running;
                return Task.FromResult<PipelineTask?>(task);
            }
        }
        return Task.FromResult<PipelineTask?>(null);
    }
    
    public Task CompleteAsync(string taskId, string result)
    {
        lock (_lock)
        {
            if (_tasks.TryGetValue(taskId, out var task))
            {
                task.Status = core.TaskStatus.Completed;
                task.Result = result;
                task.CompletedAt = DateTime.UtcNow;
                task.Progress = 100;
            }
        }
        return Task.CompletedTask;
    }
    
    public Task FailAsync(string taskId, string error)
    {
        lock (_lock)
        {
            if (_tasks.TryGetValue(taskId, out var task))
            {
                task.Status = core.TaskStatus.Failed;
                task.CompletedAt = DateTime.UtcNow;
            }
        }
        return Task.CompletedTask;
    }
    
    public IEnumerable<PipelineTask> GetPendingTasks()
    {
        lock (_lock)
        {
            return _tasks.Values.Where(t => t.Status == core.TaskStatus.Pending).ToList();
        }
    }
    
    public IEnumerable<PipelineTask> GetCompletedTasks()
    {
        lock (_lock)
        {
            return _tasks.Values.Where(t => t.Status == core.TaskStatus.Completed).ToList();
        }
    }
}
