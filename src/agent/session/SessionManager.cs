using Microsoft.Extensions.Logging;
using System.Text.Json.Serialization;

namespace agent.session;


/// <summary>
/// 会话管理器实现
/// </summary>
public class SessionManager : ISessionManager
{
    private readonly ILogger<SessionManager> _logger;
    private readonly Dictionary<string, Session> _sessions = new();
    private readonly Dictionary<string, SessionLoop> _loops = new();
    private readonly object _lock = new();
    
    /// <summary>共享 loop logger (v7.8): 消灭每次创建会话时的 LoggerFactory 构建</summary>
    private static readonly ILogger<SessionLoop> SharedLoopLogger =
        LoggerFactory.Create(b => b.AddConsole()).CreateLogger<SessionLoop>();
    
    public SessionManager(ILogger<SessionManager> logger)
    {
        _logger = logger;
    }
    
    public Task<Session> CreateSessionAsync(string userId, SessionConfig? config = null)
    {
        config ??= new SessionConfig();
        
        var session = new Session
        {
            UserId = userId,
            State = core.SessionState.Active,
            Metadata = new Dictionary<string, object>
            {
                { "maxTokens", config.MaxTokens },
                { "timeout", config.Timeout },
                { "memoryMaxChars", config.MaxMemoryChars }
            }
        };
        
        lock (_lock)
        {
            _sessions[session.Id] = session;
            // SessionLoop 懒创建 (v7.8): 无消费者启动前不实例化, 也不构建重量级 LoggerFactory
        }
        
        _logger.LogInformation("Created session {SessionId} for user {UserId}", session.Id, userId);
        
        return Task.FromResult(session);
    }
    
    public Task<Session?> GetSessionAsync(string sessionId)
    {
        lock (_lock)
        {
            _sessions.TryGetValue(sessionId, out var session);
            return Task.FromResult(session);
        }
    }
    
    public Task<Session> GetOrCreateSessionAsync(string sessionId, string userId)
    {
        lock (_lock)
        {
            if (_sessions.TryGetValue(sessionId, out var existing))
                return Task.FromResult(existing);
            
            var session = new Session
            {
                Id = sessionId, // 调用方指定 Id (与 message.SessionId 对齐, 多轮历史才能命中)
                UserId = userId,
                State = core.SessionState.Active,
                Metadata = new Dictionary<string, object>
                {
                    { "maxTokens", new SessionConfig().MaxTokens },
                    { "timeout", new SessionConfig().Timeout }
                }
            };
            _sessions[sessionId] = session;
            _logger.LogInformation("Auto-created session {SessionId} for user {UserId}", sessionId, userId);
            return Task.FromResult(session);
        }
    }
    
    public Task UpdateSessionAsync(Session session)
    {
        lock (_lock)
        {
            session.LastActivityAt = DateTime.UtcNow;
            _sessions[session.Id] = session;
        }
        
        return Task.CompletedTask;
    }
    
    public Task EndSessionAsync(string sessionId)
    {
        lock (_lock)
        {
            if (_sessions.TryGetValue(sessionId, out var session))
            {
                session.State = core.SessionState.Completed;
            }
            
            // 真删除 (v7.8): 已终结会话保留在字典 = 内存泄漏。历史归档走持久化层, 不靠内存字典
            _sessions.Remove(sessionId);
            
            if (_loops.Remove(sessionId, out var loop))
            {
                _ = loop.StopAsync();
            }
        }
        
        _logger.LogInformation("Ended session {SessionId}", sessionId);
        
        return Task.CompletedTask;
    }
    
    public Task<SessionLoop> GetSessionLoopAsync(string sessionId)
    {
        lock (_lock)
        {
            if (_loops.TryGetValue(sessionId, out var loop))
                return Task.FromResult(loop);
            
            // 懒创建 (v7.8): 会话存在时按需实例化 loop; 会话不存在才抛错
            if (_sessions.ContainsKey(sessionId))
            {
                var created = new SessionLoop(sessionId, this, SharedLoopLogger);
                _loops[sessionId] = created;
                return Task.FromResult(created);
            }
        }
        
        throw new InvalidOperationException($"Session loop {sessionId} not found");
    }
    
    public Task<IEnumerable<Session>> GetUserSessionsAsync(string userId)
    {
        lock (_lock)
        {
            var sessions = _sessions.Values
                .Where(s => s.UserId == userId)
                .OrderByDescending(s => s.LastActivityAt);
            
            return Task.FromResult<IEnumerable<Session>>(sessions.ToList());
        }
    }

    public Task<IEnumerable<Session>> GetAllSessionsAsync()
    {
        lock (_lock)
        {
            var sessions = _sessions.Values.OrderByDescending(s => s.LastActivityAt);
            return Task.FromResult<IEnumerable<Session>>(sessions.ToList());
        }
    }
}
