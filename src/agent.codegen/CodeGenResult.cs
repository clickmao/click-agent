using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 代码生成结果
/// </summary>
public class CodeGenResult
{
    public bool Success { get; set; }
    public string? Code { get; set; }
    public string? Error { get; set; }
    public string? FilePath { get; set; }
    public List<CodeChange> Changes { get; set; } = new();
    public Dictionary<string, object> Metadata { get; set; } = new();
}
