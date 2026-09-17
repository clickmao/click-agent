using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 成员类型
/// </summary>
public enum MemberKind
{
    Class,
    Interface,
    Struct,
    Enum,
    Method,
    Property,
    Field,
    Constructor,
    Destructor,
    Event,
    Indexer
}
