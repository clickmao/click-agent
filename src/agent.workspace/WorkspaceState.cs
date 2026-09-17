using Microsoft.Extensions.Logging;

namespace agent.workspace;

/// <summary>
/// 工作区状态
/// </summary>
public enum WorkspaceState
{
    Initial,
    Loading,
    Ready,
    Busy,
    Error
}
