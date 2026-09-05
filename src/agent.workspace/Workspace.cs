using Microsoft.Extensions.Logging;
using System.Text.RegularExpressions;
using agent.userinteraction;

namespace agent.workspace;

/// <summary>
/// 工作区实现
/// </summary>
public class Workspace : IWorkspace
{
    private readonly ILogger<Workspace> _logger;
    private WorkspaceContext _context = new();
    private WorkspaceState _state = WorkspaceState.Initial;
    private readonly Dictionary<string, string> _fileCache = new();
    private readonly object _cacheLock = new();
    
    public WorkspaceState State => _state;
    public string RootPath => _context.RootPath;
    
    private readonly IUserPromptService? _prompts;

    public Workspace(ILogger<Workspace> logger, IUserPromptService? prompts = null)
    {
        _logger = logger;
        _prompts = prompts;
    }

    /// <summary>
    /// 敏感操作审批门禁: 删除类操作按托管级别路由 ——
    /// RealUserOnly 权威 (不可逆), Full 托管下也必须真实用户批准。
    /// 问询失败/拒绝时返回 false, 绝不继续执行。
    /// </summary>
    private async Task<bool> ApproveDeleteAsync(string fullPath, string kind)
    {
        if (_prompts is null)
        {
            _logger.LogWarning("无问询服务可用, 删除操作被拒绝 (fail-closed): {Path}", fullPath);
            return false;
        }

        var result = await _prompts.RequestOperationApprovalAsync(new SensitiveOperationRequest
        {
            Kind = kind == "file" ? SensitiveOperationKind.DeleteFile : SensitiveOperationKind.DeleteFile,
            Summary = $"删除{(kind == "file" ? "文件" : "目录")}: {fullPath}",
            Details = kind == "file"
                ? $"将永久删除文件 {fullPath} (不可恢复)"
                : $"将递归删除目录 {fullPath} 及其全部内容 (不可恢复)",
            Initiator = "Workspace",
            Origin = new PromptOrigin
            {
                AskedByAgentId = "main",
                AskingDepth = 0,
                Authority = AnswerAuthority.RealUserOnly, // 删除不可逆 → 仅真实用户
            },
        });

        return result.Approved;
    }
    
    public Task InitializeAsync(string path, CancellationToken ct = default)
    {
        try
        {
            _state = WorkspaceState.Loading;
            _context.RootPath = Path.GetFullPath(path);
            
            if (!Directory.Exists(_context.RootPath))
            {
                throw new DirectoryNotFoundException($"Workspace path not found: {_context.RootPath}");
            }
            
            _state = WorkspaceState.Ready;
            _logger.LogInformation("Workspace initialized at: {Path}", _context.RootPath);
            
            return Task.CompletedTask;
        }
        catch (Exception ex)
        {
            _state = WorkspaceState.Error;
            _logger.LogError(ex, "Failed to initialize workspace");
            throw;
        }
    }
    
    public Task<WorkspaceInfo> GetInfoAsync(CancellationToken ct = default)
    {
        var info = new WorkspaceInfo
        {
            RootPath = _context.RootPath,
            LastModified = DateTime.UtcNow
        };
        
        var sourceExtensions = new[] { ".cs", ".js", ".ts", ".py", ".java", ".go", ".rs", ".cpp", ".c" };
        var testExtensions = new[] { ".test.cs", ".spec.js", ".test.js", "_test.py", ".test.ts" };
        var configExtensions = new[] { ".json", ".yaml", ".yml", ".xml", ".toml", ".config" };
        
        foreach (var ext in sourceExtensions)
        {
            info.SourceFiles.AddRange(Directory.GetFiles(_context.RootPath, $"*{ext}", SearchOption.AllDirectories)
                .Where(f => !f.Contains("node_modules") && !f.Contains("bin") && !f.Contains("obj")));
        }
        
        foreach (var ext in testExtensions)
        {
            info.TestFiles.AddRange(Directory.GetFiles(_context.RootPath, $"*{ext}", SearchOption.AllDirectories)
                .Where(f => !f.Contains("node_modules")));
        }
        
        foreach (var ext in configExtensions)
        {
            info.ConfigFiles.AddRange(Directory.GetFiles(_context.RootPath, $"*{ext}", SearchOption.TopDirectoryOnly)
                .Where(f => !f.Contains("node_modules")));
        }
        
        info.TotalLines = info.SourceFiles.Sum(f => 
        {
            try { return File.ReadAllLines(f).Length; }
            catch { return 0; }
        });
        
        // 检测语言和框架
        if (info.SourceFiles.Any(f => f.EndsWith(".cs")))
        {
            info.Language = "C#";
            if (File.Exists(Path.Combine(_context.RootPath, "*.csproj")))
            {
                info.Framework = "dotnet";
            }
        }
        else if (info.SourceFiles.Any(f => f.EndsWith(".js") || f.EndsWith(".ts")))
        {
            info.Language = info.SourceFiles.Any(f => f.EndsWith(".ts")) ? "TypeScript" : "JavaScript";
            if (File.Exists(Path.Combine(_context.RootPath, "package.json")))
            {
                info.Framework = "node";
            }
        }
        
        return Task.FromResult(info);
    }
    
    public async Task<FileOperationResult> ReadFileAsync(string path, CancellationToken ct = default)
    {
        var fullPath = GetFullPath(path);
        
        try
        {
            string content;
            long fileSize;
            
            // 尝试从缓存读取
            lock (_cacheLock)
            {
                if (_fileCache.TryGetValue(fullPath, out var cachedContent))
                {
                    content = cachedContent;
                    fileSize = new FileInfo(fullPath).Length;
                    return new FileOperationResult
                    {
                        Success = true,
                        FilePath = fullPath,
                        Content = content,
                        FileSize = fileSize,
                        LastModified = File.GetLastWriteTimeUtc(fullPath)
                    };
                }
            }
            
            content = await File.ReadAllTextAsync(fullPath, ct);
            fileSize = new FileInfo(fullPath).Length;
            
            // 更新缓存
            lock (_cacheLock)
            {
                _fileCache[fullPath] = content;
            }
            
            return new FileOperationResult
            {
                Success = true,
                FilePath = fullPath,
                Content = content,
                FileSize = fileSize,
                LastModified = File.GetLastWriteTimeUtc(fullPath)
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to read file: {Path}", fullPath);
            return new FileOperationResult
            {
                Success = false,
                Error = ex.Message,
                FilePath = fullPath
            };
        }
    }
    
    public async Task<FileOperationResult> WriteFileAsync(string path, string content, CancellationToken ct = default)
    {
        var fullPath = GetFullPath(path);
        
        try
        {
            // 确保目录存在
            var directory = Path.GetDirectoryName(fullPath);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }
            
            await File.WriteAllTextAsync(fullPath, content, ct);
            
            // 更新缓存
            lock (_cacheLock)
            {
                _fileCache[fullPath] = content;
            }
            
            _logger.LogInformation("File written: {Path}", fullPath);
            
            return new FileOperationResult
            {
                Success = true,
                FilePath = fullPath,
                Content = content,
                FileSize = new FileInfo(fullPath).Length,
                LastModified = DateTime.UtcNow
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to write file: {Path}", fullPath);
            return new FileOperationResult
            {
                Success = false,
                Error = ex.Message,
                FilePath = fullPath
            };
        }
    }
    
    public Task<FileOperationResult> CreateFileAsync(string path, string content, CancellationToken ct = default)
    {
        if (File.Exists(GetFullPath(path)))
        {
            return Task.FromResult(new FileOperationResult
            {
                Success = false,
                Error = "File already exists",
                FilePath = GetFullPath(path)
            });
        }
        
        return WriteFileAsync(path, content, ct);
    }
    
    public async Task<FileOperationResult> DeleteFileAsync(string path, CancellationToken ct = default)
    {
        var fullPath = GetFullPath(path);
        
        try
        {
            if (!File.Exists(fullPath))
            {
                return new FileOperationResult
                {
                    Success = false,
                    Error = "File not found",
                    FilePath = fullPath
                };
            }
            
            // 敏感操作门禁: 删除前必须获得真实用户批准
            if (!await ApproveDeleteAsync(fullPath, "file"))
            {
                return new FileOperationResult
                {
                    Success = false,
                    Error = "Operation denied: 用户未批准删除操作",
                    FilePath = fullPath
                };
            }
            
            File.Delete(fullPath);
            
            // 清除缓存
            lock (_cacheLock)
            {
                _fileCache.Remove(fullPath);
            }
            
            _logger.LogInformation("File deleted: {Path}", fullPath);
            
            return new FileOperationResult
            {
                Success = true,
                FilePath = fullPath
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to delete file: {Path}", fullPath);
            return new FileOperationResult
            {
                Success = false,
                Error = ex.Message,
                FilePath = fullPath
            };
        }
    }
    
    public Task<FileOperationResult> MoveFileAsync(string source, string destination, CancellationToken ct = default)
    {
        var srcPath = GetFullPath(source);
        var destPath = GetFullPath(destination);
        
        try
        {
            var directory = Path.GetDirectoryName(destPath);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }
            
            File.Move(srcPath, destPath);
            
            // 更新缓存
            lock (_cacheLock)
            {
                if (_fileCache.TryGetValue(srcPath, out var content))
                {
                    _fileCache.Remove(srcPath);
                    _fileCache[destPath] = content;
                }
            }
            
            _logger.LogInformation("File moved: {Source} -> {Destination}", srcPath, destPath);
            
            return Task.FromResult(new FileOperationResult
            {
                Success = true,
                FilePath = destPath
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to move file: {Source} -> {Destination}", srcPath, destPath);
            return Task.FromResult(new FileOperationResult
            {
                Success = false,
                Error = ex.Message,
                FilePath = srcPath
            });
        }
    }
    
    public Task<FileOperationResult> CopyFileAsync(string source, string destination, CancellationToken ct = default)
    {
        var srcPath = GetFullPath(source);
        var destPath = GetFullPath(destination);
        
        try
        {
            File.Copy(srcPath, destPath, overwrite: true);
            
            _logger.LogInformation("File copied: {Source} -> {Destination}", srcPath, destPath);
            
            return Task.FromResult(new FileOperationResult
            {
                Success = true,
                FilePath = destPath
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to copy file: {Source} -> {Destination}", srcPath, destPath);
            return Task.FromResult(new FileOperationResult
            {
                Success = false,
                Error = ex.Message,
                FilePath = srcPath
            });
        }
    }
    
    public Task<bool> FileExistsAsync(string path, CancellationToken ct = default)
    {
        return Task.FromResult(File.Exists(GetFullPath(path)));
    }
    
    public Task<List<string>> ListDirectoryAsync(string path, bool recursive = false, CancellationToken ct = default)
    {
        var fullPath = string.IsNullOrEmpty(path) ? _context.RootPath : GetFullPath(path);
        
        try
        {
            var searchOption = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            var files = Directory.GetFiles(fullPath, "*", searchOption)
                .Where(f => !f.Contains("node_modules") && !f.Contains(".git") && !f.Contains("bin") && !f.Contains("obj"))
                .ToList();
            
            return Task.FromResult(files);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to list directory: {Path}", fullPath);
            return Task.FromResult(new List<string>());
        }
    }
    
    public Task<List<string>> SearchFilesAsync(string pattern, CancellationToken ct = default)
    {
        try
        {
            var regex = new WildcardToRegex(pattern);
            var files = Directory.GetFiles(_context.RootPath, "*", SearchOption.AllDirectories)
                .Where(f => regex.IsMatch(Path.GetFileName(f)))
                .Where(f => !f.Contains("node_modules") && !f.Contains(".git"))
                .ToList();
            
            return Task.FromResult(files);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to search files: {Pattern}", pattern);
            return Task.FromResult(new List<string>());
        }
    }
    
    public async Task<List<SearchResult>> SearchContentAsync(string pattern, CancellationToken ct = default)
    {
        var results = new List<SearchResult>();
        var regex = new Regex(pattern, RegexOptions.IgnoreCase);
        
        try
        {
            var files = Directory.GetFiles(_context.RootPath, "*.*", SearchOption.AllDirectories)
                .Where(f => !f.Contains("node_modules") && !f.Contains(".git") && !f.Contains("bin") && !f.Contains("obj"))
                .Where(f => IsTextFile(f));
            
            foreach (var file in files)
            {
                ct.ThrowIfCancellationRequested();
                
                try
                {
                    var lines = await File.ReadAllLinesAsync(file, ct);
                    
                    for (int i = 0; i < lines.Length; i++)
                    {
                        var matches = regex.Matches(lines[i]);
                        
                        foreach (Match match in matches)
                        {
                            results.Add(new SearchResult
                            {
                                FilePath = file,
                                LineNumber = i + 1,
                                Content = lines[i],
                                MatchStart = match.Index,
                                MatchEnd = match.Index + match.Length
                            });
                        }
                    }
                }
                catch { /* 跳过无法读取的文件 */ }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to search content: {Pattern}", pattern);
        }
        
        return results;
    }
    
    public async Task<string> GetFileDiffAsync(string path, CancellationToken ct = default)
    {
        var fullPath = GetFullPath(path);
        
        try
        {
            // 简化实现：返回当前文件内容
            var content = await File.ReadAllTextAsync(fullPath, ct);
            return $"--- {path}\n+++ {path}\n{content}";
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get file diff: {Path}", fullPath);
            return string.Empty;
        }
    }
    
    public Task<bool> CreateDirectoryAsync(string path, CancellationToken ct = default)
    {
        var fullPath = GetFullPath(path);
        
        try
        {
            Directory.CreateDirectory(fullPath);
            _logger.LogInformation("Directory created: {Path}", fullPath);
            return Task.FromResult(true);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create directory: {Path}", fullPath);
            return Task.FromResult(false);
        }
    }
    
    public async Task<bool> DeleteDirectoryAsync(string path, CancellationToken ct = default)
    {
        var fullPath = GetFullPath(path);
        
        try
        {
            // 敏感操作门禁: 递归删除前必须获得真实用户批准
            if (!await ApproveDeleteAsync(fullPath, "directory"))
            {
                _logger.LogInformation("Directory deletion denied by user: {Path}", fullPath);
                return false;
            }
            
            Directory.Delete(fullPath, recursive: true);
            _logger.LogInformation("Directory deleted: {Path}", fullPath);
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to delete directory: {Path}", fullPath);
            return false;
        }
    }
    
    public WorkspaceContext GetContext() => _context;
    
    public void SetCurrentFile(string? path)
    {
        _context.CurrentFile = path;
        
        if (!string.IsNullOrEmpty(path) && !_context.OpenFiles.Contains(path))
        {
            _context.OpenFiles.Add(path);
        }
    }
    
    private string GetFullPath(string path)
    {
        if (Path.IsPathRooted(path))
            return path;
        return Path.GetFullPath(Path.Combine(_context.RootPath, path));
    }
    
    private bool IsTextFile(string path)
    {
        var textExtensions = new[] { ".cs", ".js", ".ts", ".py", ".java", ".go", ".rs", ".json", ".xml", ".yaml", ".yml", ".md", ".txt", ".html", ".css", ".sql", ".sh", ".ps1" };
        return textExtensions.Contains(Path.GetExtension(path).ToLowerInvariant());
    }
    
    private class WildcardToRegex
    {
        private readonly Regex _regex;
        
        public WildcardToRegex(string pattern)
        {
            var regexPattern = "^" + Regex.Escape(pattern)
                .Replace("\\*\\*", ".*")
                .Replace("\\*", "[^/]*")
                .Replace("\\?", ".") + "$";
            
            _regex = new Regex(regexPattern, RegexOptions.IgnoreCase);
        }
        
        public bool IsMatch(string input) => _regex.IsMatch(input);
    }
}
