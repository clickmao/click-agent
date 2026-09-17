using Microsoft.Extensions.Logging;

namespace agent.workspace;


/// <summary>
/// Git变更
/// </summary>
public class GitChange
{
    public string Path { get; set; } = string.Empty;
    public GitChangeType ChangeType { get; set; }
    public string? OldPath { get; set; }
}
