using Microsoft.Extensions.Logging;

namespace agent.planner;

/// <summary>
/// 交互点类型
/// </summary>
public enum InteractionPointType
{
    /// <summary>任务确认 - 开始前确认</summary>
    TaskConfirmation,
    
    /// <summary>进度通知 - 执行中定期通知</summary>
    ProgressNotification,
    
    /// <summary>结果确认 - 完成前确认</summary>
    ResultConfirmation,
    
    /// <summary>错误确认 - 出错时确认</summary>
    ErrorConfirmation,
    
    /// <summary>选择确认 - 多选项时确认</summary>
    SelectionConfirmation,
    
    /// <summary>保存确认 - 保存前确认</summary>
    SaveConfirmation,
    
    /// <summary>放弃确认 - 放弃前确认</summary>
    AbandonConfirmation
}

/// <summary>
/// 交互点
/// </summary>
public class InteractionPoint
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string TaskId { get; set; } = string.Empty;
    public InteractionPointType Type { get; set; }
    public string Title { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public string? Details { get; set; }
    public List<InteractionOption> Options { get; set; } = new();
    public string? DefaultOptionId { get; set; }
    public TimeSpan? Timeout { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? RespondedAt { get; set; }
    public string? SelectedOptionId { get; set; }
    public string? UserComment { get; set; }
    public bool IsRequired { get; set; } = true;
}

/// <summary>
/// 交互选项
/// </summary>
public class InteractionOption
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Label { get; set; } = string.Empty;
    public string? Description { get; set; }
    public bool IsRecommended { get; set; }
    public bool IsDestructive { get; set; }
    public Dictionary<string, object> Metadata { get; set; } = new();
}

/// <summary>
/// 交互管理器接口
/// </summary>
public interface IInteractionManager
{
    /// <summary>
    /// 创建交互点
    /// </summary>
    Task<InteractionPoint> CreateInteractionAsync(
        string taskId,
        InteractionPointType type,
        string title,
        string message,
        List<InteractionOption>? options = null,
        string? defaultOptionId = null,
        bool isRequired = true,
        TimeSpan? timeout = null);
    
    /// <summary>
    /// 获取待处理的交互点
    /// </summary>
    Task<List<InteractionPoint>> GetPendingInteractionsAsync(string sessionId);
    
    /// <summary>
    /// 获取交互点
    /// </summary>
    Task<InteractionPoint?> GetInteractionAsync(string interactionId);
    
    /// <summary>
    /// 响应交互点
    /// </summary>
    Task<bool> RespondAsync(string interactionId, string optionId, string? comment = null);
    
    /// <summary>
    /// 跳过交互点（仅对非必需的交互点）
    /// </summary>
    Task<bool> SkipAsync(string interactionId);
    
    /// <summary>
    /// 获取任务的所有交互历史
    /// </summary>
    Task<List<InteractionPoint>> GetInteractionHistoryAsync(string taskId);
    
    /// <summary>
    /// 等待交互响应
    /// </summary>
    Task<InteractionPoint?> WaitForResponseAsync(string interactionId, CancellationToken ct);
}

/// <summary>
/// 用户反馈记录
/// </summary>
public class UserFeedback
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string SessionId { get; set; } = string.Empty;
    public string TaskId { get; set; } = string.Empty;
    public string InteractionId { get; set; } = string.Empty;
    public string SelectedOptionId { get; set; } = string.Empty;
    public string? SelectedOptionLabel { get; set; }
    public string? UserComment { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public List<string> Keywords { get; set; } = new();
    public string Context { get; set; } = string.Empty;
    public string TaskDescription { get; set; } = string.Empty;
    public string? Outcome { get; set; }
    public double? Satisfaction { get; set; }
    public Dictionary<string, object> Metadata { get; set; } = new();
}

/// <summary>
/// 反馈存储接口
/// </summary>
public interface IFeedbackStore
{
    /// <summary>
    /// 存储反馈
    /// </summary>
    Task<string> StoreAsync(UserFeedback feedback);
    
    /// <summary>
    /// 查询相似反馈
    /// </summary>
    Task<List<UserFeedback>> QuerySimilarAsync(string query, int topK = 5);
    
    /// <summary>
    /// 查询任务相关的反馈
    /// </summary>
    Task<List<UserFeedback>> QueryByTaskAsync(string taskId);
    
    /// <summary>
    /// 获取用户的反馈历史
    /// </summary>
    Task<List<UserFeedback>> GetUserHistoryAsync(string userId, int count = 50);
    
    /// <summary>
    /// 更新反馈（添加结果或满意度）
    /// </summary>
    Task UpdateAsync(UserFeedback feedback);
}

/// <summary>
/// 交互管理器实现
/// </summary>
public class InteractionManager : IInteractionManager
{
    private readonly ILogger<InteractionManager> _logger;
    private readonly IFeedbackStore _feedbackStore;
    private readonly Dictionary<string, InteractionPoint> _interactions = new();
    private readonly Dictionary<string, TaskCompletionSource<InteractionPoint>> _waiters = new();
    private readonly object _lock = new();
    
    public InteractionManager(ILogger<InteractionManager> logger, IFeedbackStore feedbackStore)
    {
        _logger = logger;
        _feedbackStore = feedbackStore;
    }
    
    public Task<InteractionPoint> CreateInteractionAsync(
        string taskId,
        InteractionPointType type,
        string title,
        string message,
        List<InteractionOption>? options = null,
        string? defaultOptionId = null,
        bool isRequired = true,
        TimeSpan? timeout = null)
    {
        var interaction = new InteractionPoint
        {
            TaskId = taskId,
            Type = type,
            Title = title,
            Message = message,
            Options = options ?? GetDefaultOptions(type),
            DefaultOptionId = defaultOptionId,
            IsRequired = isRequired,
            Timeout = timeout ?? TimeSpan.FromMinutes(5)
        };
        
        lock (_lock)
        {
            _interactions[interaction.Id] = interaction;
        }
        
        _logger.LogInformation("Created interaction {InteractionId} for task {TaskId}: {Title}", 
            interaction.Id, taskId, title);
        
        return Task.FromResult(interaction);
    }
    
    public Task<List<InteractionPoint>> GetPendingInteractionsAsync(string sessionId)
    {
        lock (_lock)
        {
            var pending = _interactions.Values
                .Where(i => i.RespondedAt == null)
                .OrderBy(i => i.CreatedAt)
                .ToList();
            
            return Task.FromResult(pending);
        }
    }
    
    public Task<InteractionPoint?> GetInteractionAsync(string interactionId)
    {
        lock (_lock)
        {
            _interactions.TryGetValue(interactionId, out var interaction);
            return Task.FromResult(interaction);
        }
    }
    
    public Task<bool> RespondAsync(string interactionId, string optionId, string? comment = null)
    {
        InteractionPoint? interaction;
        
        lock (_lock)
        {
            if (!_interactions.TryGetValue(interactionId, out interaction))
            {
                return Task.FromResult(false);
            }
            
            if (interaction.Options.All(o => o.Id != optionId))
            {
                _logger.LogWarning("Invalid option {OptionId} for interaction {InteractionId}", optionId, interactionId);
                return Task.FromResult(false);
            }
            
            interaction.RespondedAt = DateTime.UtcNow;
            interaction.SelectedOptionId = optionId;
            interaction.UserComment = comment;
        }
        
        _logger.LogInformation("User responded to interaction {InteractionId}: {OptionId}", interactionId, optionId);
        
        // 通知等待者
        if (_waiters.TryGetValue(interactionId, out var tcs))
        {
            tcs.TrySetResult(interaction);
        }
        
        return Task.FromResult(true);
    }
    
    public Task<bool> SkipAsync(string interactionId)
    {
        lock (_lock)
        {
            if (!_interactions.TryGetValue(interactionId, out var interaction))
            {
                return Task.FromResult(false);
            }
            
            if (interaction.IsRequired)
            {
                _logger.LogWarning("Cannot skip required interaction {InteractionId}", interactionId);
                return Task.FromResult(false);
            }
            
            interaction.RespondedAt = DateTime.UtcNow;
            interaction.SelectedOptionId = "skip";
        }
        
        if (_waiters.TryGetValue(interactionId, out var tcs))
        {
            tcs.TrySetResult(null!);
        }
        
        return Task.FromResult(true);
    }
    
    public Task<List<InteractionPoint>> GetInteractionHistoryAsync(string taskId)
    {
        lock (_lock)
        {
            var history = _interactions.Values
                .Where(i => i.TaskId == taskId)
                .OrderBy(i => i.CreatedAt)
                .ToList();
            
            return Task.FromResult(history);
        }
    }
    
    public async Task<InteractionPoint?> WaitForResponseAsync(string interactionId, CancellationToken ct)
    {
        var tcs = new TaskCompletionSource<InteractionPoint>();
        
        lock (_lock)
        {
            _waiters[interactionId] = tcs;
        }
        
        try
        {
            using var timeoutCts = new CancellationTokenSource(TimeSpan.FromMinutes(5));
            using var linkedCts = CancellationTokenSource.CreateLinkedTokenSource(ct, timeoutCts.Token);
            
            return await tcs.Task;
        }
        catch (TaskCanceledException)
        {
            _logger.LogWarning("Wait for interaction {InteractionId} timed out", interactionId);
            return null;
        }
        finally
        {
            lock (_lock)
            {
                _waiters.Remove(interactionId);
            }
        }
    }
    
    private List<InteractionOption> GetDefaultOptions(InteractionPointType type)
    {
        return type switch
        {
            InteractionPointType.TaskConfirmation => new List<InteractionOption>
            {
                new() { Id = "confirm", Label = "确认开始", IsRecommended = true },
                new() { Id = "modify", Label = "修改需求" },
                new() { Id = "cancel", Label = "取消" }
            },
            InteractionPointType.ResultConfirmation => new List<InteractionOption>
            {
                new() { Id = "approve", Label = "确认完成", IsRecommended = true },
                new() { Id = "retry", Label = "重新执行" },
                new() { Id = "modify", Label = "修改结果" }
            },
            InteractionPointType.SaveConfirmation => new List<InteractionOption>
            {
                new() { Id = "save", Label = "保存", IsRecommended = true },
                new() { Id = "discard", Label = "不保存", IsDestructive = true },
                new() { Id = "modify", Label = "修改" }
            },
            InteractionPointType.ErrorConfirmation => new List<InteractionOption>
            {
                new() { Id = "retry", Label = "重试", IsRecommended = true },
                new() { Id = "skip", Label = "跳过" },
                new() { Id = "abort", Label = "终止任务", IsDestructive = true }
            },
            _ => new List<InteractionOption>
            {
                new() { Id = "ok", Label = "确定", IsRecommended = true },
                new() { Id = "cancel", Label = "取消" }
            }
        };
    }
}

/// <summary>
/// 反馈存储实现（基于向量记忆）
/// </summary>
public class FeedbackStore : IFeedbackStore
{
    private readonly ILogger<FeedbackStore> _logger;
    private readonly Dictionary<string, UserFeedback> _store = new();
    private readonly object _lock = new();
    
    public FeedbackStore(ILogger<FeedbackStore> logger)
    {
        _logger = logger;
    }
    
    public Task<string> StoreAsync(UserFeedback feedback)
    {
        if (string.IsNullOrEmpty(feedback.Id))
        {
            feedback.Id = Guid.NewGuid().ToString();
        }
        
        // 提取关键词
        feedback.Keywords = ExtractKeywords(feedback.TaskDescription);
        feedback.Keywords.AddRange(ExtractKeywords(feedback.Context));
        
        lock (_lock)
        {
            _store[feedback.Id] = feedback;
        }
        
        _logger.LogInformation("Stored feedback {FeedbackId} for task {TaskId}", feedback.Id, feedback.TaskId);
        
        return Task.FromResult(feedback.Id);
    }
    
    public Task<List<UserFeedback>> QuerySimilarAsync(string query, int topK = 5)
    {
        var queryKeywords = ExtractKeywords(query);
        var scores = new Dictionary<string, double>();
        
        lock (_lock)
        {
            foreach (var feedback in _store.Values)
            {
                var score = CalculateSimilarity(queryKeywords, feedback.Keywords);
                if (score > 0.3)
                {
                    scores[feedback.Id] = score;
                }
            }
        }
        
        var results = scores
            .OrderByDescending(kv => kv.Value)
            .Take(topK)
            .Select(kv =>
            {
                lock (_lock)
                {
                    _store.TryGetValue(kv.Key, out var f);
                    return f;
                }
            })
            .OfType<UserFeedback>()
            .ToList();
        
        return Task.FromResult(results);
    }
    
    public Task<List<UserFeedback>> QueryByTaskAsync(string taskId)
    {
        lock (_lock)
        {
            var feedbacks = _store.Values
                .Where(f => f.TaskId == taskId)
                .OrderByDescending(f => f.CreatedAt)
                .ToList();
            
            return Task.FromResult(feedbacks);
        }
    }
    
    public Task<List<UserFeedback>> GetUserHistoryAsync(string userId, int count = 50)
    {
        lock (_lock)
        {
            var history = _store.Values
                .OrderByDescending(f => f.CreatedAt)
                .Take(count)
                .ToList();
            
            return Task.FromResult(history);
        }
    }
    
    public Task UpdateAsync(UserFeedback feedback)
    {
        lock (_lock)
        {
            _store[feedback.Id] = feedback;
        }
        
        return Task.CompletedTask;
    }
    
    private List<string> ExtractKeywords(string text)
    {
        if (string.IsNullOrEmpty(text)) return new List<string>();
        
        // 简单的关键词提取
        var keywords = new HashSet<string>();
        
        // 提取长词
        var words = text.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        foreach (var word in words)
        {
            if (word.Length >= 3)
            {
                keywords.Add(word.ToLowerInvariant());
            }
        }
        
        // 提取CamelCase
        var camelMatches = System.Text.RegularExpressions.Regex.Matches(text, @"[A-Z][a-z]+");
        foreach (System.Text.RegularExpressions.Match match in camelMatches)
        {
            keywords.Add(match.Value.ToLowerInvariant());
        }
        
        return keywords.ToList();
    }
    
    private double CalculateSimilarity(List<string> queryKeywords, List<string> itemKeywords)
    {
        if (!queryKeywords.Any() || !itemKeywords.Any()) return 0;
        
        var intersection = queryKeywords.Intersect(itemKeywords, StringComparer.OrdinalIgnoreCase).Count();
        var union = queryKeywords.Union(itemKeywords, StringComparer.OrdinalIgnoreCase).Count();
        
        return union > 0 ? (double)intersection / union : 0;
    }
}
