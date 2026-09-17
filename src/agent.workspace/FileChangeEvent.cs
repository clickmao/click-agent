using Microsoft.Extensions.Logging;

namespace agent.workspace;


/// <summary>
/// 文件变更事件
/// </summary>
public class FileChangeEvent
{
    public string FilePath { get; set; } = string.Empty;
    public FileChangeType ChangeType { get; set; }
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    public string? OldPath { get; set; }
    public long? FileSize { get; set; }
    public string? Content { get; set; }
}
