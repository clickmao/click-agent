using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 代码生成类型
/// </summary>
public enum CodeGenType
{
    Class,
    Interface,
    Struct,
    Enum,
    Record,
    Method,
    Property,
    Field,
    Constructor,
    File
}
