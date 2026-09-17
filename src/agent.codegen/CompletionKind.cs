using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 补全类型
/// </summary>
public enum CompletionKind
{
    Keyword,
    Class,
    Interface,
    Method,
    Property,
    Field,
    Variable,
    Function,
    Snippet,
    Module,
    Constant,
    Type
}
