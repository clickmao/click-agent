using Microsoft.Extensions.Logging;

namespace agent.recovery;

/// <summary>
/// 错误信息
/// </summary>
public class ErrorInfo
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Message { get; set; } = string.Empty;
    public string? StackTrace { get; set; }
    public ErrorType Type { get; set; }
    public ErrorSeverity Severity { get; set; }
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    public Dictionary<string, object> Context { get; set; } = new();
    public List<string> PossibleCauses { get; set; } = new();
    public RecoveryAction? SuggestedRecovery { get; set; }
}

/// <summary>
/// 错误类型
/// </summary>
public enum ErrorType
{
    Syntax,
    Runtime,
    Network,
    FileSystem,
    Authentication,
    Authorization,
    Validation,
    Timeout,
    Resource,
    Unknown
}

/// <summary>
/// 错误严重性
/// </summary>
public enum ErrorSeverity
{
    Hint,
    Warning,
    Error,
    Critical
}

/// <summary>
/// 恢复操作
/// </summary>
public class RecoveryAction
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public RecoveryStrategy Strategy { get; set; }
    public int Priority { get; set; }
    public bool IsAutomatic { get; set; }
    public Func<Task<RecoveryResult>> ExecuteAsync { get; set; } = () => Task.FromResult(new RecoveryResult());
}

/// <summary>
/// 恢复策略
/// </summary>
public enum RecoveryStrategy
{
    Retry,
    RetryWithBackoff,
    Skip,
    Fallback,
    Rollback,
    UserConfirmation,
    Cancel
}

/// <summary>
/// 恢复结果
/// </summary>
public class RecoveryResult
{
    public bool Success { get; set; }
    public string? Error { get; set; }
    public int Attempts { get; set; }
    public TimeSpan Duration { get; set; }
    public string? ActionTaken { get; set; }
}

/// <summary>
/// 重试策略配置
/// </summary>
public class RetryPolicy
{
    public int MaxAttempts { get; set; } = 3;
    public TimeSpan InitialDelay { get; set; } = TimeSpan.FromSeconds(1);
    public TimeSpan MaxDelay { get; set; } = TimeSpan.FromMinutes(1);
    public double BackoffMultiplier { get; set; } = 2.0;
    public bool ExponentialBackoff { get; set; } = true;
    public Func<Exception, bool>? ShouldRetry { get; set; }
}

/// <summary>
/// 回滚点
/// </summary>
public class RollbackPoint
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Operation { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public string State { get; set; } = string.Empty;
    public Dictionary<string, object> Metadata { get; set; } = new();
    public Func<Task<bool>> RollbackAction { get; set; } = () => Task.FromResult(true);
}

/// <summary>
/// 错误分类器
/// </summary>
public class ErrorClassifier
{
    private readonly Dictionary<string, ErrorPattern> _patterns = new();
    
    public ErrorClassifier()
    {
        InitializePatterns();
    }
    
    public ErrorInfo Classify(Exception exception, Dictionary<string, object>? context = null)
    {
        var info = new ErrorInfo
        {
            Message = exception.Message,
            StackTrace = exception.StackTrace,
            Timestamp = DateTime.UtcNow,
            Context = context ?? new Dictionary<string, object>()
        };
        
        foreach (var (key, pattern) in _patterns)
        {
            if (pattern.Matcher(exception))
            {
                info.Type = pattern.Type;
                info.Severity = pattern.Severity;
                info.PossibleCauses = pattern.PossibleCauses;
                info.SuggestedRecovery = pattern.GetRecoveryAction();
                return info;
            }
        }
        
        info.Type = ErrorType.Unknown;
        info.Severity = ErrorSeverity.Error;
        return info;
    }
    
    private void InitializePatterns()
    {
        // 网络错误
        _patterns["network"] = new ErrorPattern
        {
            Type = ErrorType.Network,
            Severity = ErrorSeverity.Error,
            Matcher = ex => ex.Message.Contains("network") || 
                          ex.Message.Contains("connection") ||
                          ex is System.Net.Http.HttpRequestException,
            PossibleCauses = new List<string> { "网络连接失败", "服务器不可达", "DNS解析失败" },
            GetRecoveryAction = () => new RecoveryAction
            {
                Name = "Retry with backoff",
                Strategy = RecoveryStrategy.RetryWithBackoff,
                Priority = 1,
                IsAutomatic = true
            }
        };
        
        // 超时错误
        _patterns["timeout"] = new ErrorPattern
        {
            Type = ErrorType.Timeout,
            Severity = ErrorSeverity.Warning,
            Matcher = ex => ex.Message.Contains("timeout") ||
                          ex is TimeoutException ||
                          ex.Message.Contains("timed out"),
            PossibleCauses = new List<string> { "操作超时", "服务响应慢", "网络延迟" },
            GetRecoveryAction = () => new RecoveryAction
            {
                Name = "Retry",
                Strategy = RecoveryStrategy.Retry,
                Priority = 2,
                IsAutomatic = true
            }
        };
        
        // 文件系统错误
        _patterns["filesystem"] = new ErrorPattern
        {
            Type = ErrorType.FileSystem,
            Severity = ErrorSeverity.Error,
            Matcher = ex => ex is System.IO.IOException ||
                          ex is System.IO.FileNotFoundException ||
                          ex is System.IO.DirectoryNotFoundException,
            PossibleCauses = new List<string> { "文件不存在", "权限不足", "磁盘空间不足" },
            GetRecoveryAction = () => new RecoveryAction
            {
                Name = "Check file exists",
                Strategy = RecoveryStrategy.Fallback,
                Priority = 3,
                IsAutomatic = false
            }
        };
        
        // 语法错误
        _patterns["syntax"] = new ErrorPattern
        {
            Type = ErrorType.Syntax,
            Severity = ErrorSeverity.Error,
            Matcher = ex => ex.Message.Contains("syntax") ||
                          ex.Message.Contains("unexpected token") ||
                          ex.Message.Contains("parse"),
            PossibleCauses = new List<string> { "语法错误", "格式不正确", "缺少符号" },
            GetRecoveryAction = () => new RecoveryAction
            {
                Name = "Fix syntax",
                Strategy = RecoveryStrategy.Skip,
                Priority = 1,
                IsAutomatic = false
            }
        };
        
        // 认证错误
        _patterns["auth"] = new ErrorPattern
        {
            Type = ErrorType.Authentication,
            Severity = ErrorSeverity.Critical,
            Matcher = ex => ex.Message.Contains("unauthorized") ||
                          ex.Message.Contains("authentication") ||
                          ex.Message.Contains("credential"),
            PossibleCauses = new List<string> { "认证失败", "Token过期", "权限不足" },
            GetRecoveryAction = () => new RecoveryAction
            {
                Name = "User confirmation required",
                Strategy = RecoveryStrategy.UserConfirmation,
                Priority = 1,
                IsAutomatic = false
            }
        };
    }
}

/// <summary>
/// 错误模式
/// </summary>
public class ErrorPattern
{
    public ErrorType Type { get; set; }
    public ErrorSeverity Severity { get; set; }
    public Func<Exception, bool> Matcher { get; set; } = _ => false;
    public List<string> PossibleCauses { get; set; } = new();
    public Func<RecoveryAction> GetRecoveryAction { get; set; } = () => new RecoveryAction();
}

/// <summary>
/// 错误恢复系统接口
/// </summary>
public interface IRecoverySystem
{
    /// <summary>
    /// 记录错误
    /// </summary>
    Task<ErrorInfo> RecordErrorAsync(Exception exception, Dictionary<string, object>? context = null);
    
    /// <summary>
    /// 获取恢复建议
    /// </summary>
    Task<List<RecoveryAction>> GetRecoveryActionsAsync(string errorId);
    
    /// <summary>
    /// 执行恢复
    /// </summary>
    Task<RecoveryResult> ExecuteRecoveryAsync(string errorId, RecoveryAction action);
    
    /// <summary>
    /// 创建回滚点
    /// </summary>
    Task<string> CreateRollbackPointAsync(string operation, string state, Dictionary<string, object>? metadata = null);
    
    /// <summary>
    /// 回滚到指定点
    /// </summary>
    Task<bool> RollbackToAsync(string rollbackPointId);
    
    /// <summary>
    /// 获取错误历史
    /// </summary>
    Task<List<ErrorInfo>> GetErrorHistoryAsync(int count = 50);
}

/// <summary>
/// 错误恢复系统实现
/// </summary>
public class RecoverySystem : IRecoverySystem
{
    private readonly ILogger<RecoverySystem> _logger;
    private readonly ErrorClassifier _classifier = new();
    private readonly Dictionary<string, ErrorInfo> _errors = new();
    private readonly Stack<RollbackPoint> _rollbackStack = new();
    private readonly RetryPolicy _defaultRetryPolicy;
    
    public RecoverySystem(ILogger<RecoverySystem> logger)
    {
        _logger = logger;
        _defaultRetryPolicy = new RetryPolicy
        {
            MaxAttempts = 3,
            InitialDelay = TimeSpan.FromSeconds(1),
            BackoffMultiplier = 2.0,
            ExponentialBackoff = true
        };
    }
    
    public Task<ErrorInfo> RecordErrorAsync(Exception exception, Dictionary<string, object>? context = null)
    {
        var errorInfo = _classifier.Classify(exception, context);
        
        lock (_errors)
        {
            _errors[errorInfo.Id] = errorInfo;
        }
        
        _logger.LogError(exception, "Error recorded: {ErrorId} - {Message}", errorInfo.Id, errorInfo.Message);
        
        return Task.FromResult(errorInfo);
    }
    
    public Task<List<RecoveryAction>> GetRecoveryActionsAsync(string errorId)
    {
        var actions = new List<RecoveryAction>();
        
        lock (_errors)
        {
            if (_errors.TryGetValue(errorId, out var error))
            {
                if (error.SuggestedRecovery != null)
                {
                    actions.Add(error.SuggestedRecovery);
                }
                
                // 添加通用恢复策略
                actions.Add(new RecoveryAction
                {
                    Name = "Retry",
                    Strategy = RecoveryStrategy.Retry,
                    Priority = 1,
                    IsAutomatic = true
                });
                
                actions.Add(new RecoveryAction
                {
                    Name = "Skip",
                    Strategy = RecoveryStrategy.Skip,
                    Priority = 2,
                    IsAutomatic = false
                });
                
                actions.Add(new RecoveryAction
                {
                    Name = "Cancel",
                    Strategy = RecoveryStrategy.Cancel,
                    Priority = 3,
                    IsAutomatic = true
                });
            }
        }
        
        return Task.FromResult(actions.OrderBy(a => a.Priority).ToList());
    }
    
    public async Task<RecoveryResult> ExecuteRecoveryAsync(string errorId, RecoveryAction action)
    {
        var result = new RecoveryResult { ActionTaken = action.Name };
        var startTime = DateTime.UtcNow;
        
        try
        {
            switch (action.Strategy)
            {
                case RecoveryStrategy.Retry:
                    result = await ExecuteRetryAsync(_defaultRetryPolicy);
                    break;
                    
                case RecoveryStrategy.RetryWithBackoff:
                    var backoffPolicy = new RetryPolicy
                    {
                        MaxAttempts = 5,
                        InitialDelay = TimeSpan.FromSeconds(2),
                        BackoffMultiplier = 2.0,
                        ExponentialBackoff = true
                    };
                    result = await ExecuteRetryAsync(backoffPolicy);
                    break;
                    
                case RecoveryStrategy.Skip:
                    _logger.LogInformation("Skipping failed operation");
                    result.Success = true;
                    break;
                    
                case RecoveryStrategy.Rollback:
                    if (_rollbackStack.Count > 0)
                    {
                        var rollbackPoint = _rollbackStack.Pop();
                        result.Success = await rollbackPoint.RollbackAction();
                    }
                    else
                    {
                        result.Success = false;
                        result.Error = "No rollback points available";
                    }
                    break;
                    
                case RecoveryStrategy.Cancel:
                    result.Success = true;
                    break;
                    
                default:
                    result.Success = false;
                    result.Error = $"Unknown recovery strategy: {action.Strategy}";
                    break;
            }
        }
        catch (Exception ex)
        {
            result.Success = false;
            result.Error = ex.Message;
        }
        
        result.Duration = DateTime.UtcNow - startTime;
        return result;
    }
    
    public Task<string> CreateRollbackPointAsync(string operation, string state, Dictionary<string, object>? metadata = null)
    {
        var point = new RollbackPoint
        {
            Operation = operation,
            State = state,
            Metadata = metadata ?? new Dictionary<string, object>()
        };
        
        lock (_rollbackStack)
        {
            _rollbackStack.Push(point);
        }
        
        _logger.LogInformation("Created rollback point: {PointId} - {Operation}", point.Id, operation);
        
        return Task.FromResult(point.Id);
    }
    
    public async Task<bool> RollbackToAsync(string rollbackPointId)
    {
        RollbackPoint? target = null;
        var skipped = new List<RollbackPoint>();

        // 临界区只做栈操作 (查找+摘除), 回调在锁外执行 (lock 内禁止 await)
        lock (_rollbackStack)
        {
            while (_rollbackStack.Count > 0)
            {
                var point = _rollbackStack.Pop();
                if (point.Id == rollbackPointId)
                {
                    target = point;
                    break;
                }
                skipped.Add(point);
            }

            // 未找到: 全部放回
            if (target is null)
            {
                for (var i = skipped.Count - 1; i >= 0; i--)
                    _rollbackStack.Push(skipped[i]);
            }
        }

        if (target is null)
            return false;

        var success = await target.RollbackAction();

        // 成功则丢弃被跳过的点 (回滚语义: 目标之后的点一并失效); 失败则恢复原栈
        if (!success)
        {
            lock (_rollbackStack)
            {
                for (var i = skipped.Count - 1; i >= 0; i--)
                    _rollbackStack.Push(skipped[i]);
                _rollbackStack.Push(target);
            }
        }

        return success;
    }
    
    public Task<List<ErrorInfo>> GetErrorHistoryAsync(int count = 50)
    {
        lock (_errors)
        {
            var errors = _errors.Values
                .OrderByDescending(e => e.Timestamp)
                .Take(count)
                .ToList();
            
            return Task.FromResult(errors);
        }
    }
    
    private async Task<RecoveryResult> ExecuteRetryAsync(RetryPolicy policy)
    {
        var result = new RecoveryResult();
        var delay = policy.InitialDelay;
        
        for (int attempt = 1; attempt <= policy.MaxAttempts; attempt++)
        {
            result.Attempts = attempt;
            
            try
            {
                // 模拟重试
                await Task.Delay(delay);
                
                // 检查是否应该重试
                if (policy.ShouldRetry != null)
                {
                    // 这里应该传入实际发生的异常
                    break;
                }
                
                result.Success = true;
                return result;
            }
            catch (Exception)
            {
                if (attempt == policy.MaxAttempts)
                {
                    result.Success = false;
                    result.Error = $"Max retry attempts ({policy.MaxAttempts}) reached";
                    return result;
                }
                
                // 等待后重试
                await Task.Delay(delay);
                
                if (policy.ExponentialBackoff)
                {
                    delay = TimeSpan.FromTicks((long)(delay.Ticks * policy.BackoffMultiplier));
                }
                else
                {
                    delay = TimeSpan.FromTicks(delay.Ticks + policy.InitialDelay.Ticks);
                }
                
                delay = delay > policy.MaxDelay ? policy.MaxDelay : delay;
            }
        }
        
        return result;
    }
}
