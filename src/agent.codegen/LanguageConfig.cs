using Microsoft.Extensions.Logging;
using System.Text;
using System.Text.RegularExpressions;

namespace agent.codegen;


/// <summary>
/// 语言配置
/// </summary>
public class LanguageConfig
{
    public string Name { get; set; } = string.Empty;
    public string[] Extensions { get; set; } = Array.Empty<string>();
    public string CommentSingle { get; set; } = "//";
    public string CommentStart { get; set; } = "/*";
    public string CommentEnd { get; set; } = "*/";
    public int IndentSize { get; set; } = 4;
}
