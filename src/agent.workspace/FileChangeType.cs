using Microsoft.Extensions.Logging;

namespace agent.workspace;


/// <summary>
/// 文件变更类型
/// </summary>
public enum FileChangeType
{
    Created,
    Modified,
    Deleted,
    Renamed
}
