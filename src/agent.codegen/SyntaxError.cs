using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 语法错误
/// </summary>
public class SyntaxError
{
    public int Line { get; set; }
    public int Column { get; set; }
    public string Message { get; set; } = string.Empty;
    public string Severity { get; set; } = "error";
    public string? Code { get; set; }
}
