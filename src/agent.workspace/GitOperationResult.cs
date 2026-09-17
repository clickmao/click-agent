using Microsoft.Extensions.Logging;

namespace agent.workspace;


/// <summary>
/// Git操作结果
/// </summary>
public class GitOperationResult
{
    public bool Success { get; set; }
    public string? Error { get; set; }
    public string Output { get; set; } = string.Empty;
    public string? FilePath { get; set; }
}
