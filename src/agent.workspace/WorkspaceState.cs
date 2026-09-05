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

/// <summary>
/// 文件变更类型
/// </summary>
public enum FileChangeType
{
    Created,
    Modified,
    Deleted,
    Renamed
}

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

/// <summary>
/// 工作区接口
/// </summary>
public interface IWorkspace
{
    /// <summary>
    /// 工作区状态
    /// </summary>
    WorkspaceState State { get; }
    
    /// <summary>
    /// 工作区根路径
    /// </summary>
    string RootPath { get; }
    
    /// <summary>
    /// 初始化工作区
    /// </summary>
    Task InitializeAsync(string path, CancellationToken ct = default);
    
    /// <summary>
    /// 获取工作区信息
    /// </summary>
    Task<WorkspaceInfo> GetInfoAsync(CancellationToken ct = default);
    
    /// <summary>
    /// 读取文件
    /// </summary>
    Task<FileOperationResult> ReadFileAsync(string path, CancellationToken ct = default);
    
    /// <summary>
    /// 写入文件
    /// </summary>
    Task<FileOperationResult> WriteFileAsync(string path, string content, CancellationToken ct = default);
    
    /// <summary>
    /// 创建文件
    /// </summary>
    Task<FileOperationResult> CreateFileAsync(string path, string content, CancellationToken ct = default);
    
    /// <summary>
    /// 删除文件
    /// </summary>
    Task<FileOperationResult> DeleteFileAsync(string path, CancellationToken ct = default);
    
    /// <summary>
    /// 移动文件
    /// </summary>
    Task<FileOperationResult> MoveFileAsync(string source, string destination, CancellationToken ct = default);
    
    /// <summary>
    /// 复制文件
    /// </summary>
    Task<FileOperationResult> CopyFileAsync(string source, string destination, CancellationToken ct = default);
    
    /// <summary>
    /// 检查文件是否存在
    /// </summary>
    Task<bool> FileExistsAsync(string path, CancellationToken ct = default);
    
    /// <summary>
    /// 列出目录内容
    /// </summary>
    Task<List<string>> ListDirectoryAsync(string path, bool recursive = false, CancellationToken ct = default);
    
    /// <summary>
    /// 搜索文件
    /// </summary>
    Task<List<string>> SearchFilesAsync(string pattern, CancellationToken ct = default);
    
    /// <summary>
    /// 搜索文件内容
    /// </summary>
    Task<List<SearchResult>> SearchContentAsync(string pattern, CancellationToken ct = default);
    
    /// <summary>
    /// 获取文件差异
    /// </summary>
    Task<string> GetFileDiffAsync(string path, CancellationToken ct = default);
    
    /// <summary>
    /// 创建目录
    /// </summary>
    Task<bool> CreateDirectoryAsync(string path, CancellationToken ct = default);
    
    /// <summary>
    /// 删除目录
    /// </summary>
    Task<bool> DeleteDirectoryAsync(string path, CancellationToken ct = default);
    
    /// <summary>
    /// 获取上下文
    /// </summary>
    WorkspaceContext GetContext();
    
    /// <summary>
    /// 设置当前文件
    /// </summary>
    void SetCurrentFile(string? path);
}

/// <summary>
/// 搜索结果
/// </summary>
public class SearchResult
{
    public string FilePath { get; set; } = string.Empty;
    public int LineNumber { get; set; }
    public string Content { get; set; } = string.Empty;
    public int MatchStart { get; set; }
    public int MatchEnd { get; set; }
}
