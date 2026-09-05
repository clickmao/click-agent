using Microsoft.Extensions.Logging;
using System.Text.Json.Serialization;

namespace agent.session;

/// <summary>
/// 会话模型
/// </summary>
public class Session
{
    /// <summary>
    /// 会话ID
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();

    /// <summary>
    /// 用户ID
    /// </summary>
    public string UserId { get; set; } = string.Empty;

    /// <summary>
    /// 会话状态
    /// </summary>
    public core.SessionState State { get; set; } = core.SessionState.Initial;

    /// <summary>
    /// 创建时间
    /// </summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    /// <summary>
    /// 最后活动时间
    /// </summary>
    public DateTime LastActivityAt { get; set; } = DateTime.UtcNow;

    /// <summary>
    /// 轮次计数
    /// </summary>
    public int TurnCount { get; set; }

    /// <summary>
    /// Token使用量
    /// </summary>
    public long TokenUsage { get; set; }

    /// <summary>
    /// 消息列表
    /// </summary>
    public List<core.Message> Messages { get; set; } = new();

    /// <summary>
    /// 元数据
    /// </summary>
    public Dictionary<string, object> Metadata { get; set; } = new();

    /// <summary>会话长期记忆 + 任务目标画像 (v7.14, 懒创建; 上限由 MemoryMaxChars 控制)</summary>
    [JsonIgnore]
    public SessionMemory Memory
    {
        get
        {
            if (_memory == null)
            {
                var cap = Metadata.TryGetValue("memoryMaxChars", out var v) && v is int i ? i : SessionMemory.DefaultMaxChars;
                _memory = new SessionMemory(cap);
            }
            return _memory;
        }
    }

    [JsonIgnore]
    private SessionMemory? _memory;

    /// <summary>
    /// ✅ 添加用户消息
    /// </summary>
    public void AddUserMessage(string content)
    {
        Messages.Add(new core.Message
        {
            Id = Guid.NewGuid().ToString(),
            SessionId = Id,
            SenderId = UserId,
            Role = core.MessageRole.User,
            Content = content,
            Type = core.MessageType.Text,
            Timestamp = DateTime.UtcNow
        });
        TurnCount++;
        LastActivityAt = DateTime.UtcNow;
        TrimHistory();
    }

    /// <summary>
    /// ✅ 添加助手消息
    /// </summary>
    public void AddAssistantMessage(string content, string? senderId = null)
    {
        Messages.Add(new core.Message
        {
            Id = Guid.NewGuid().ToString(),
            SessionId = Id,
            SenderId = senderId ?? "assistant",
            Role = core.MessageRole.Assistant,
            Content = content,
            Type = core.MessageType.Text,
            Timestamp = DateTime.UtcNow
        });
        LastActivityAt = DateTime.UtcNow;
        TrimHistory();
    }

    /// <summary>
    /// 消息历史上限保护 (v7.8): 长会话内存无界增长防线。
    /// 超限裁剪最旧消息; 完整归档属持久化层职责, 不由内存会话承担。
    /// </summary>
    private void TrimHistory()
    {
        if (Messages.Count <= MaxHistoryMessages)
            return;
        
        var excess = Messages.Count - MaxHistoryMessages;
        Messages.RemoveRange(0, excess);
    }

    /// <summary>单会话消息历史上限</summary>
    public const int MaxHistoryMessages = 200;

    /// <summary>
    /// ✅ 获取最近的对话
    /// </summary>
    public List<core.Message> GetRecentMessages(int count = 10)
    {
        // v7.8: Messages 追加序 = 时间序, 直接倒序取尾部 (O(k)) 替代全表排序 (O(N log N))
        var result = new List<core.Message>(Math.Min(count, Messages.Count));
        for (var i = Messages.Count - 1; i >= 0 && result.Count < count; i--)
            result.Add(Messages[i]);
        result.Reverse();
        return result;
    }

    /// <summary>
    /// ✅ 获取相关消息（基于关键词）
    /// </summary>
    public List<core.Message> GetRelevantMessages(string query, int count = 5)
    {
        var keywords = query.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        // v7.8: 命中过滤在前 (O(N*M)), 排序只作用于命中子集 — 原实现对全表排序
        var matches = new List<core.Message>();
        foreach (var m in Messages)
        {
            if (m.Role == core.MessageRole.System)
                continue;
            foreach (var k in keywords)
            {
                if (m.Content.Contains(k, StringComparison.OrdinalIgnoreCase))
                {
                    matches.Add(m);
                    break;
                }
            }
        }
        
        matches.Sort(static (a, b) => b.Timestamp.CompareTo(a.Timestamp));
        if (matches.Count > count)
            matches.RemoveRange(count, matches.Count - count);
        return matches;
    }
    
    /// <summary>
    /// ✅ 添加用户消息（异步版本）
    /// </summary>
    public async Task AddUserMessageAsync(string content)
    {
        AddUserMessage(content);
        LastActivityAt = DateTime.UtcNow;
        await Task.CompletedTask;
    }
    
    /// <summary>
    /// ✅ 添加助手消息（异步版本）
    /// </summary>
    public async Task AddAssistantMessageAsync(string content, string? senderId = null)
    {
        AddAssistantMessage(content, senderId);
        LastActivityAt = DateTime.UtcNow;
        await Task.CompletedTask;
    }
    
    /// <summary>
    /// ✅ 获取对话摘要
    /// </summary>
    public string GetConversationSummary(int maxLength = 200)
    {
        var recent = GetRecentMessages(5);
        var summary = string.Join("\n", recent.Select(m => 
            $"[{m.Role}] {m.Content}"));
        
        if (summary.Length > maxLength)
            return summary[..maxLength] + "...";
        
        return summary;
    }
}

/// <summary>
/// 会话配置
/// </summary>
public class SessionConfig
{
    /// <summary>
    /// 最大Token数
    /// </summary>
    public long MaxTokens { get; set; } = 100000;
    
    /// <summary>
    /// 超时时间
    /// </summary>
    public TimeSpan Timeout { get; set; } = TimeSpan.FromHours(1);
    
    /// <summary>
    /// 会话长期记忆上限字符数 (v7.14): 默认 1000, 可配置 (100..10000)
    /// </summary>
    public int MaxMemoryChars { get; set; } = SessionMemory.DefaultMaxChars;

    /// <summary>
    /// 是否自动保存
    /// </summary>
    public bool AutoSave { get; set; } = true;
    
    /// <summary>
    /// 保存间隔
    /// </summary>
    public TimeSpan SaveInterval { get; set; } = TimeSpan.FromMinutes(1);
}

/// <summary>
/// 会话管理器接口
/// </summary>
public interface ISessionManager
{
    /// <summary>
    /// 创建会话
    /// </summary>
    Task<Session> CreateSessionAsync(string userId, SessionConfig? config = null);
    
    /// <summary>
    /// 获取会话
    /// </summary>
    Task<Session?> GetSessionAsync(string sessionId);
    
    /// <summary>
    /// 获取或创建会话 (幂等: 指定 Id 不存在时以该 Id 创建, 保证多轮对话历史不因会话缺失而静默丢失)
    /// </summary>
    Task<Session> GetOrCreateSessionAsync(string sessionId, string userId);
    
    /// <summary>
    /// 更新会话
    /// </summary>
    Task UpdateSessionAsync(Session session);
    
    /// <summary>
    /// 结束会话
    /// </summary>
    Task EndSessionAsync(string sessionId);
    
    /// <summary>
    /// 获取会话循环
    /// </summary>
    Task<SessionLoop> GetSessionLoopAsync(string sessionId);
    
    /// <summary>
    /// 获取用户的所有会话
    /// </summary>
    Task<IEnumerable<Session>> GetUserSessionsAsync(string userId);

    /// <summary>
    /// 获取全部会话 (v7.14 面板: /session 需要跨用户枚举)
    /// </summary>
    Task<IEnumerable<Session>> GetAllSessionsAsync();
}

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
