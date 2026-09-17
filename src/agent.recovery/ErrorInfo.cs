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
