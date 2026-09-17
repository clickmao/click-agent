using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 代码成员
/// </summary>
public class CodeMember
{
    public string Name { get; set; } = string.Empty;
    public MemberKind Kind { get; set; }
    public int Line { get; set; }
    public int EndLine { get; set; }
    public string? AccessModifier { get; set; }
    public string? ReturnType { get; set; }
    public List<CodeMember> Children { get; set; } = new();
}
