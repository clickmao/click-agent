using Microsoft.Extensions.Logging;

namespace agent.recovery;


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
