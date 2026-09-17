using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 代码模板
/// </summary>
public class CodeTemplate
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Name { get; set; } = string.Empty;
    public string Language { get; set; } = string.Empty;
    public CodeGenType Type { get; set; }
    public string Pattern { get; set; } = string.Empty;
    public string Template { get; set; } = string.Empty;
    public List<string> RequiredParameters { get; set; } = new();
    public List<string> OptionalParameters { get; set; } = new();
    public string? Description { get; set; }
    public int UsageCount { get; set; }
}
