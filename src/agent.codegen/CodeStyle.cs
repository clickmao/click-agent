using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 代码风格（用于上下文感知生成）
/// </summary>
public class CodeStyle
{
    public NamingConvention NamingConvention { get; set; } = NamingConvention.PascalCase;
    public bool UseRegions { get; set; } = false;
    public CommentStyle CommentStyle { get; set; } = CommentStyle.SingleLine;
    public bool UseNullable { get; set; } = true;
}
