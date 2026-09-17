using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 符号类型
/// </summary>
public enum SymbolKind
{
    Namespace,
    Class,
    Interface,
    Struct,
    Enum,
    Method,
    Property,
    Field,
    Variable,
    Parameter,
    TypeParameter
}
