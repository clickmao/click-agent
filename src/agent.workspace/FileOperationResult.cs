using Microsoft.Extensions.Logging;

namespace agent.workspace;


/// <summary>
/// 文件操作结果
/// </summary>
public class FileOperationResult
{
    public bool Success { get; set; }
    public string? Error { get; set; }
    public string? FilePath { get; set; }
    public string? Content { get; set; }
    public long? FileSize { get; set; }
    public DateTime? LastModified { get; set; }
}
