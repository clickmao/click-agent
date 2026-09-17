using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 变更类型
/// </summary>
public enum ChangeType
{
    Created,
    Modified,
    Deleted,
    Renamed
}
