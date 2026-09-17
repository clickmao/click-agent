using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 代码生成请求
/// </summary>
public class CodeGenRequest
{
    public string Description { get; set; } = string.Empty;
    public CodeGenType Type { get; set; } = CodeGenType.Class;
    public string? TemplateName { get; set; }
    public Dictionary<string, object> Parameters { get; set; } = new();
    public CodeGenOptions Options { get; set; } = new();
    public List<string>? Imports { get; set; }
    public string? BaseClass { get; set; }
    public List<string>? Interfaces { get; set; }
    public List<string>? Attributes { get; set; }
}
