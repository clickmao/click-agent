using Microsoft.Extensions.Logging;

namespace agent.recovery;


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
