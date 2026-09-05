using Microsoft.Extensions.Logging;

namespace agent.core;

/// <summary>
/// Agent基类抽象
/// </summary>
public abstract class AgentBase : IAgent
{
    protected readonly ILogger<AgentBase> _logger;
    protected readonly IEnumerable<IMessageHandler> _handlers;
    
    private AgentState _state = AgentState.Initial;
    
    public string Id { get; protected set; } = Guid.NewGuid().ToString();
    public string Name { get; protected set; } = "Agent";
    public AgentState State
    {
        get => _state;
        protected set
        {
            if (_state != value)
            {
                var oldState = _state;
                _state = value;
                OnStateChanged(oldState, value);
            }
        }
    }
    
    public event EventHandler<AgentStateChangedEventArgs>? StateChanged;
    public event EventHandler<Message>? MessageReceived;
    
    protected AgentBase(ILogger<AgentBase> logger, IEnumerable<IMessageHandler> handlers)
    {
        _logger = logger;
        _handlers = handlers;
    }
    
    /// <summary>
    /// 初始化Agent
    /// </summary>
    public virtual async Task InitializeAsync(IAgentContext context, CancellationToken ct = default)
    {
        try
        {
            State = AgentState.Initializing;
            _logger.LogInformation("Initializing agent {AgentId} ({AgentName})", Id, Name);
            
            await OnInitializeAsync(context, ct);
            
            State = AgentState.Ready;
            _logger.LogInformation("Agent {AgentId} initialized successfully", Id);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to initialize agent {AgentId}", Id);
            State = AgentState.Error;
            throw;
        }
    }
    
    /// <summary>
    /// 处理消息
    /// </summary>
    public virtual async Task<AgentResponse> ProcessAsync(Message message, CancellationToken ct = default)
    {
        if (State != AgentState.Ready && State != AgentState.Processing)
        {
            return AgentResponse.ErrorResponse($"Agent is not in ready state. Current state: {State}");
        }
        
        try
        {
            State = AgentState.Processing;
            MessageReceived?.Invoke(this, message);
            
            _logger.LogDebug("Processing message from {SenderId}: {ContentPreview}", 
                message.SenderId, 
                message.Content.Length > 100 ? message.Content[..100] + "..." : message.Content);
            
            var response = await OnProcessAsync(message, ct);
            
            State = AgentState.Ready;
            return response;
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Message processing cancelled for {MessageId}", message.Id);
            State = AgentState.Ready;
            return AgentResponse.ErrorResponse("Operation was cancelled");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing message {MessageId}", message.Id);
            State = AgentState.Error;
            return AgentResponse.ErrorResponse(ex.Message);
        }
    }
    
    /// <summary>
    /// 执行子任务
    /// </summary>
    public virtual async Task<AgentResponse> ExecuteTaskAsync(subagent.SubAgentTask task, CancellationToken ct = default)
    {
        try
        {
            _logger.LogInformation("Executing task {TaskId}: {TaskName}", task.Id, task.Name);
            
            var response = await OnExecuteTaskAsync(task, ct);
            
            _logger.LogInformation("Task {TaskId} completed with success={Success}", task.Id, response.Success);
            return response;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error executing task {TaskId}", task.Id);
            return AgentResponse.ErrorResponse(ex.Message);
        }
    }
    
    /// <summary>
    /// 路由消息
    /// </summary>
    public virtual async Task<AgentResponse> RouteAsync(Message message, CancellationToken ct = default)
    {
        foreach (var handler in _handlers)
        {
            if (await handler.CanHandleAsync(message, ct))
            {
                return await handler.HandleAsync(message, ct);
            }
        }
        
        return await ProcessAsync(message, ct);
    }
    
    /// <summary>
    /// 关闭Agent
    /// </summary>
    public virtual async Task ShutdownAsync(CancellationToken ct = default)
    {
        try
        {
            _logger.LogInformation("Shutting down agent {AgentId}", Id);
            State = AgentState.Shutdown;
            await OnShutdownAsync(ct);
            _logger.LogInformation("Agent {AgentId} shutdown completed", Id);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error shutting down agent {AgentId}", Id);
            throw;
        }
    }
    
    /// <summary>
    /// 子类初始化钩子
    /// </summary>
    protected virtual Task OnInitializeAsync(IAgentContext context, CancellationToken ct)
    {
        return Task.CompletedTask;
    }
    
    /// <summary>
    /// 子类消息处理钩子
    /// </summary>
    protected abstract Task<AgentResponse> OnProcessAsync(Message message, CancellationToken ct);
    
    /// <summary>
    /// 子类任务执行钩子
    /// </summary>
    protected virtual Task<AgentResponse> OnExecuteTaskAsync(subagent.SubAgentTask task, CancellationToken ct)
    {
        return Task.FromResult(AgentResponse.ErrorResponse("Task execution not implemented"));
    }
    
    /// <summary>
    /// 子类关闭钩子
    /// </summary>
    protected virtual Task OnShutdownAsync(CancellationToken ct)
    {
        return Task.CompletedTask;
    }
    
    /// <summary>
    /// 状态变更通知
    /// </summary>
    protected virtual void OnStateChanged(AgentState oldState, AgentState newState)
    {
        _logger.LogDebug("Agent {AgentId} state changed from {OldState} to {NewState}", Id, oldState, newState);
        StateChanged?.Invoke(this, new AgentStateChangedEventArgs
        {
            AgentId = Id,
            OldState = oldState,
            NewState = newState
        });
    }
}

/// <summary>
/// 消息处理器接口
/// </summary>
public interface IMessageHandler
{
    /// <summary>
    /// 是否能处理该消息
    /// </summary>
    Task<bool> CanHandleAsync(Message message, CancellationToken ct = default);
    
    /// <summary>
    /// 处理消息
    /// </summary>
    Task<AgentResponse> HandleAsync(Message message, CancellationToken ct = default);
    
    /// <summary>
    /// 优先级（数字越小优先级越高）
    /// </summary>
    int Priority { get; }
}
