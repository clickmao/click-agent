using Microsoft.Extensions.Logging;

namespace agent.workspace;


/// <summary>
/// Git分支信息
/// </summary>
public class GitBranch
{
    public string Name { get; set; } = string.Empty;
    public bool IsCurrent { get; set; }
    public string? Upstream { get; set; }
    public int? AheadCount { get; set; }
    public int? BehindCount { get; set; }
}
