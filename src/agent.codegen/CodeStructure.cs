using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 代码结构
/// </summary>
public class CodeStructure
{
    public List<CodeMember> Members { get; set; } = new();
    public List<string> Usings { get; set; } = new();
    public string? Namespace { get; set; }
    public string? ClassName { get; set; }
    public List<string> BaseTypes { get; set; } = new();
}
