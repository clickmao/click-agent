using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 代码问题
/// </summary>
public class CodeIssue
{
    public string RuleId { get; set; } = string.Empty;
    public int Line { get; set; }
    public int Column { get; set; }
    public string Message { get; set; } = string.Empty;
    public IssueSeverity Severity { get; set; }
    public string? Suggestion { get; set; }
}
