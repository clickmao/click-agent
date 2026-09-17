using Microsoft.Extensions.Logging;

namespace agent.workspace;


/// <summary>
/// 工作区信息
/// </summary>
public class WorkspaceInfo
{
    public string RootPath { get; set; } = string.Empty;
    public List<string> SourceFiles { get; set; } = new();
    public List<string> TestFiles { get; set; } = new();
    public List<string> ConfigFiles { get; set; } = new();
    public string? Language { get; set; }
    public string? Framework { get; set; }
    public Dictionary<string, string> Dependencies { get; set; } = new();
    public long TotalLines { get; set; }
    public DateTime LastModified { get; set; }
}
