using Microsoft.Extensions.Logging;

namespace agent.workspace;


/// <summary>
/// 工作区上下文
/// </summary>
public class WorkspaceContext
{
    public string RootPath { get; set; } = string.Empty;
    public string? CurrentFile { get; set; }
    public List<string> OpenFiles { get; set; } = new();
    public Dictionary<string, object> Variables { get; set; } = new();
    public Dictionary<string, string> Aliases { get; set; } = new();
    public string? GitBranch { get; set; }
    public string? GitCommit { get; set; }
}
