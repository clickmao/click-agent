using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 问题严重性
/// </summary>
public enum IssueSeverity
{
    Hint,
    Info,
    Warning,
    Error
}
