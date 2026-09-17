using Microsoft.Extensions.Logging;

namespace agent.codegen;

/// <summary>
/// 代码生成选项
/// </summary>
public class CodeGenOptions
{
    public string Language { get; set; } = "csharp";
    public bool AddComments { get; set; } = true;
    public bool FormatCode { get; set; } = true;
    public string NamingConvention { get; set; } = "PascalCase";
    public bool GenerateTests { get; set; } = false;
    public int MaxLineLength { get; set; } = 120;
}
