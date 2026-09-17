using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 符号
/// </summary>
public class Symbol
{
    public string Name { get; set; } = string.Empty;
    public SymbolKind Kind { get; set; }
    public string? Type { get; set; }
    public int Line { get; set; }
    public string? Definition { get; set; }
}
