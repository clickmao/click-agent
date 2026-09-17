using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 代码补全
/// </summary>
public class CodeCompletion
{
    public string Text { get; set; } = string.Empty;
    public string DisplayText { get; set; } = string.Empty;
    public CompletionKind Kind { get; set; }
    public string? Documentation { get; set; }
    public int Priority { get; set; }
    public string? InsertText { get; set; }
    public string? Snippet { get; set; }
}
