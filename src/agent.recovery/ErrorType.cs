using Microsoft.Extensions.Logging;

namespace agent.recovery;


/// <summary>
/// 错误类型
/// </summary>
public enum ErrorType
{
    Syntax,
    Runtime,
    Network,
    FileSystem,
    Authentication,
    Authorization,
    Validation,
    Timeout,
    Resource,
    Unknown
}
