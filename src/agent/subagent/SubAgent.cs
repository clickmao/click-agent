using Microsoft.Extensions.Logging;
using agent.core;

namespace agent.subagent;

/// <summary>
/// SubAgent实现
/// </summary>
public class SubAgent : ISubAgent
{
    private readonly ILogger<SubAgent> _logger;
    private IAgentContext? _context;
    private CancellationTokenSource? _cts;
    private double _progress;
    
    public string Id { get; } = Guid.NewGuid().ToString();
    public string Name { get; set; } = "SubAgent";
    public bool IsBusy { get; private set; }
    public SubAgentTask? CurrentTask { get; private set; }
    
    public event EventHandler<double>? ProgressChanged;
    public event EventHandler<SubAgentTask>? TaskStarted;
    public event EventHandler<SubAgentTask>? TaskCompleted;
    public event EventHandler<Exception>? TaskFailed;
    
    public SubAgent(ILogger<SubAgent> logger)
    {
        _logger = logger;
    }
    
    public Task InitializeAsync(IAgentContext context, CancellationToken ct = default)
    {
        _context = context;
        _logger.LogDebug("SubAgent {AgentId} initialized for session {SessionId}", Id, context.SessionId);
        return Task.CompletedTask;
    }
    
    public async Task<AgentResponse> ExecuteAsync(SubAgentTask task, CancellationToken ct = default)
    {
        if (_context == null)
        {
            return AgentResponse.ErrorResponse("Agent not initialized");
        }
        
        CurrentTask = task;
        IsBusy = true;
        _cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        
        task.Status = core.TaskStatus.Running;
        task.StartedAt = DateTime.UtcNow;
        task.AssignedAgentId = Id;
        
        TaskStarted?.Invoke(this, task);
        
        _logger.LogInformation("SubAgent {AgentId} started executing task {TaskId}: {TaskName}", 
            Id, task.Id, task.Name);
        
        try
        {
            // 创建超时任务
            using var timeoutCts = new CancellationTokenSource(TimeSpan.FromMilliseconds(task.TimeoutMs));
            using var linkedCts = CancellationTokenSource.CreateLinkedTokenSource(ct, timeoutCts.Token);
            
            var startTime = DateTime.UtcNow;
            
            // 模拟执行（实际实现中会调用LLM或工具）
            var response = await ExecuteTaskInternalAsync(task, linkedCts.Token);
            
            // 更新任务状态
            task.Status = core.TaskStatus.Completed;
            task.CompletedAt = DateTime.UtcNow;
            task.Result = response.Content;
            task.Progress = 100;
            
            _logger.LogInformation("SubAgent {AgentId} completed task {TaskId} in {Duration}ms", 
                Id, task.Id, task.ExecutionTimeMs);
            
            TaskCompleted?.Invoke(this, task);
            
            return response;
        }
        catch (OperationCanceledException)
        {
            if (_cts?.IsCancellationRequested == true)
            {
                task.Status = core.TaskStatus.Cancelled;
                _logger.LogWarning("SubAgent {AgentId} cancelled task {TaskId}", Id, task.Id);
            }
            else
            {
                task.Status = core.TaskStatus.Timeout;
                _logger.LogWarning("SubAgent {AgentId} timed out on task {TaskId}", Id, task.Id);
            }
            
            return AgentResponse.ErrorResponse("Task was cancelled or timed out");
        }
        catch (Exception ex)
        {
            task.Status = core.TaskStatus.Failed;
            task.Error = ex.Message;
            task.CompletedAt = DateTime.UtcNow;
            
            _logger.LogError(ex, "SubAgent {AgentId} failed task {TaskId}", Id, task.Id);
            TaskFailed?.Invoke(this, ex);
            
            return AgentResponse.ErrorResponse(ex.Message);
        }
        finally
        {
            IsBusy = false;
            CurrentTask = null;
            _cts?.Dispose();
            _cts = null;
        }
    }
    
    public Task ReportProgressAsync(double progress, string? status = null)
    {
        _progress = progress;
        
        if (CurrentTask != null)
        {
            CurrentTask.Progress = progress;
            if (status != null)
            {
                _logger.LogDebug("SubAgent {AgentId} progress: {Progress}% - {Status}", 
                    Id, progress, status);
            }
        }
        
        ProgressChanged?.Invoke(this, progress);
        
        return Task.CompletedTask;
    }
    
    public async Task CancelAsync()
    {
        if (_cts != null && !_cts.IsCancellationRequested)
        {
            _logger.LogWarning("SubAgent {AgentId} cancelling current task", Id);
            await _cts.CancelAsync();
        }
    }
    
    private async Task<AgentResponse> ExecuteTaskInternalAsync(SubAgentTask task, CancellationToken ct)
    {
        _logger.LogInformation("SubAgent {AgentId} executing task: {TaskName}", Id, task.Name);
        
        try
        {
            // 分阶段执行
            await ReportProgressAsync(10, "Starting task...");
            ct.ThrowIfCancellationRequested();
            
            await ReportProgressAsync(30, "Processing input...");
            await Task.Delay(100, ct); // 模拟处理
            ct.ThrowIfCancellationRequested();
            
            await ReportProgressAsync(60, "Generating output...");
            await Task.Delay(100, ct); // 模拟生成
            ct.ThrowIfCancellationRequested();
            
            await ReportProgressAsync(90, "Finalizing...");
            await Task.Delay(50, ct); // 模拟完成
            ct.ThrowIfCancellationRequested();
            
            // ✅ 生成基于任务的实际响应
            var content = GenerateTaskResponse(task);
            
            return new AgentResponse
            {
                Content = content,
                Success = true,
                Type = MessageType.Text,
                TokensGenerated = content.Length / 4,
                ExecutionTimeMs = task.ExecutionTimeMs,
                Data = new Dictionary<string, object>
                {
                    { "subAgentId", Id },
                    { "taskType", task.Type.ToString() ?? "Unknown" }
                }
            };
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Task {TaskId} was cancelled", task.Id);
            return AgentResponse.ErrorResponse("Task was cancelled");
        }
    }
    
    /// <summary>
    /// ✅ 根据任务类型生成响应
    /// </summary>
    private string GenerateTaskResponse(SubAgentTask task)
    {
        var sb = new System.Text.StringBuilder();
        
        sb.AppendLine($"[SubAgent {Name}] Task completed:");
        sb.AppendLine();
        sb.AppendLine($"Task: {task.Name}");
        
        if (!string.IsNullOrEmpty(task.Description))
        {
            sb.AppendLine($"Description: {task.Description}");
        }
        
        if (!string.IsNullOrEmpty(task.Input))
        {
            sb.AppendLine("Input:");
            sb.AppendLine($"  {task.Input}");
        }
        
        if (task.Metadata.Any())
        {
            sb.AppendLine("Metadata:");
            foreach (var param in task.Metadata)
            {
                sb.AppendLine($"  - {param.Key}: {param.Value}");
            }
        }
        
        sb.AppendLine();
        sb.AppendLine("Result: Task executed successfully");
        
        return sb.ToString();
    }
}
