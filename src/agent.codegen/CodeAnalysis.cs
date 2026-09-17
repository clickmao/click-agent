using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 代码分析结果
/// </summary>
public class CodeAnalysis
{
    public List<SyntaxError> Errors { get; set; } = new();
    public List<SyntaxWarning> Warnings { get; set; } = new();
    public List<CodeIssue> Issues { get; set; } = new();
    public CodeStructure? Structure { get; set; }
    public List<Symbol> Symbols { get; set; } = new();
    public Dictionary<string, object> Metrics { get; set; } = new();
}
