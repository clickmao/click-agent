using Microsoft.Extensions.Logging;

namespace agent.recovery;


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
