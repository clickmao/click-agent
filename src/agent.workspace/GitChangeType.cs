using Microsoft.Extensions.Logging;

namespace agent.workspace;

/// <summary>
/// Git变更类型
/// </summary>
public enum GitChangeType
{
    Added,
    Modified,
    Deleted,
    Renamed,
    Copied
}
