using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 语法警告
/// </summary>
public class SyntaxWarning
{
    public int Line { get; set; }
    public int Column { get; set; }
    public string Message { get; set; } = string.Empty;
    public string Severity { get; set; } = "warning";
    public string? Code { get; set; }
}
