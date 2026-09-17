using Microsoft.Extensions.Logging;

namespace agent.recovery;


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
