using Microsoft.Extensions.Logging;
using System.Text.Json.Serialization;

namespace agent.session;


/// <summary>
/// 会话循环
/// </summary>
public class SessionLoop
{
    private readonly ISessionManager _sessionManager;
    private readonly ILogger<SessionLoop> _logger;
    private readonly Queue<Func<CancellationToken, Task<core.AgentResponse>>> _handlers = new();
    private CancellationTokenSource? _cts;
    
    public string SessionId { get; }
    public core.SessionLoopState State { get; private set; } = core.SessionLoopState.Stopped;
    
    public event EventHandler<core.AgentResponse>? ResponseSent;
    public event EventHandler<Exception>? Error;
    
    public SessionLoop(string sessionId, ISessionManager sessionManager, ILogger<SessionLoop> logger)
    {
        SessionId = sessionId;
        _sessionManager = sessionManager;
        _logger = logger;
    }
    
    /// <summary>
    /// 开始会话循环
    /// </summary>
    public async Task StartAsync(CancellationToken ct = default)
    {
        if (State == core.SessionLoopState.Running)
        {
            _logger.LogWarning("Session loop {SessionId} is already running", SessionId);
            return;
        }
        
        State = core.SessionLoopState.Running;
        _cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        
        _logger.LogInformation("Session loop {SessionId} started", SessionId);
        
        try
        {
            while (State == core.SessionLoopState.Running && !_cts.Token.IsCancellationRequested)
            {
                // 处理消息队列
                if (_handlers.TryDequeue(out var handler))
                {
                    var response = await handler(_cts.Token);
                    ResponseSent?.Invoke(this, response);
                }
                else
                {
                    // 没有消息时等待
                    State = core.SessionLoopState.WaitingForInput;
                    await Task.Delay(100, _cts.Token);
                    State = core.SessionLoopState.Processing;
                }
            }
        }
        catch (OperationCanceledException)
        {
            _logger.LogInformation("Session loop {SessionId} cancelled", SessionId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Session loop {SessionId} error", SessionId);
            Error?.Invoke(this, ex);
        }
        finally
        {
            State = core.SessionLoopState.Stopped;
        }
    }
    
    /// <summary>
    /// 暂停
    /// </summary>
    public Task PauseAsync()
    {
        State = core.SessionLoopState.Paused;
        _logger.LogInformation("Session loop {SessionId} paused", SessionId);
        return Task.CompletedTask;
    }
    
    /// <summary>
    /// 恢复
    /// </summary>
    public Task ResumeAsync()
    {
        if (State == core.SessionLoopState.Paused)
        {
            State = core.SessionLoopState.Running;
            _logger.LogInformation("Session loop {SessionId} resumed", SessionId);
        }
        return Task.CompletedTask;
    }
    
    /// <summary>
    /// 停止
    /// </summary>
    public Task StopAsync()
    {
        State = core.SessionLoopState.Stopped;
        _cts?.Cancel();
        _logger.LogInformation("Session loop {SessionId} stopped", SessionId);
        return Task.CompletedTask;
    }
    
    /// <summary>
    /// 入队消息处理
    /// </summary>
    public void Enqueue(Func<CancellationToken, Task<core.AgentResponse>> handler)
    {
        _handlers.Enqueue(handler);
    }
}
