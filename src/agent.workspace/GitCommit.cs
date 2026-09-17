using Microsoft.Extensions.Logging;

namespace agent.workspace;


/// <summary>
/// Git提交信息
/// </summary>
public class GitCommit
{
    public string Hash { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public string Author { get; set; } = string.Empty;
    public DateTime Date { get; set; }
    public List<string> ChangedFiles { get; set; } = new();
}
