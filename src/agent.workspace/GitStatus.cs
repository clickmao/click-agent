using Microsoft.Extensions.Logging;

namespace agent.workspace;


/// <summary>
/// Git状态
/// </summary>
public class GitStatus
{
    public string CurrentBranch { get; set; } = string.Empty;
    public List<GitChange> Changes { get; set; } = new();
    public List<string> StagedFiles { get; set; } = new();
    public List<string> UntrackedFiles { get; set; } = new();
    public bool HasConflicts { get; set; }
    public int Ahead { get; set; }
    public int Behind { get; set; }
}
