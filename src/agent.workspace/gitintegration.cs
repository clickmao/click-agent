using Microsoft.Extensions.Logging;

namespace agent.workspace;

/// <summary>
/// Git变更类型
/// </summary>
public enum GitChangeType
{
    Added,
    Modified,
    Deleted,
    Renamed,
    Copied
}

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

/// <summary>
/// Git分支信息
/// </summary>
public class GitBranch
{
    public string Name { get; set; } = string.Empty;
    public bool IsCurrent { get; set; }
    public string? Upstream { get; set; }
    public int? AheadCount { get; set; }
    public int? BehindCount { get; set; }
}

/// <summary>
/// Git变更
/// </summary>
public class GitChange
{
    public string Path { get; set; } = string.Empty;
    public GitChangeType ChangeType { get; set; }
    public string? OldPath { get; set; }
}

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

/// <summary>
/// Git集成接口
/// </summary>
public interface IGitIntegration
{
    /// <summary>
    /// 获取Git状态
    /// </summary>
    Task<GitStatus> GetStatusAsync(CancellationToken ct = default);
    
    /// <summary>
    /// 获取分支列表
    /// </summary>
    Task<List<GitBranch>> GetBranchesAsync(CancellationToken ct = default);
    
    /// <summary>
    /// 创建分支
    /// </summary>
    Task<GitOperationResult> CreateBranchAsync(string branchName, bool checkout = true, CancellationToken ct = default);
    
    /// <summary>
    /// 切换分支
    /// </summary>
    Task<GitOperationResult> CheckoutAsync(string branchName, CancellationToken ct = default);
    
    /// <summary>
    /// 添加文件到暂存区
    /// </summary>
    Task<GitOperationResult> StageAsync(string? path = null, CancellationToken ct = default);
    
    /// <summary>
    /// 取消暂存
    /// </summary>
    Task<GitOperationResult> UnstageAsync(string path, CancellationToken ct = default);
    
    /// <summary>
    /// 提交
    /// </summary>
    Task<GitOperationResult> CommitAsync(string message, CancellationToken ct = default);
    
    /// <summary>
    /// 获取提交历史
    /// </summary>
    Task<List<GitCommit>> GetLogAsync(int count = 50, CancellationToken ct = default);
    
    /// <summary>
    /// 获取文件差异
    /// </summary>
    Task<string> GetDiffAsync(string? path = null, bool staged = false, CancellationToken ct = default);
    
    /// <summary>
    /// 拉取
    /// </summary>
    Task<GitOperationResult> PullAsync(CancellationToken ct = default);
    
    /// <summary>
    /// 推送
    /// </summary>
    Task<GitOperationResult> PushAsync(CancellationToken ct = default);
    
    /// <summary>
    /// 合并
    /// </summary>
    Task<GitOperationResult> MergeAsync(string branchName, CancellationToken ct = default);
    
    /// <summary>
    /// 还原文件
    /// </summary>
    Task<GitOperationResult> RestoreAsync(string path, CancellationToken ct = default);
    
    /// <summary>
    /// 暂存特定文件
    /// </summary>
    Task<GitOperationResult> StageFileAsync(string path, CancellationToken ct = default);
    
    /// <summary>
    /// 丢弃文件更改
    /// </summary>
    Task<GitOperationResult> DiscardAsync(string path, CancellationToken ct = default);
    
    /// <summary>
    /// 创建提交（支持更详细的提交信息）
    /// </summary>
    Task<GitOperationResult> CreateCommitAsync(string message, string? description = null, CancellationToken ct = default);
    
    /// <summary>
    /// 添加所有更改
    /// </summary>
    Task<GitOperationResult> AddAllAsync(CancellationToken ct = default);
    
    /// <summary>
    /// 获取工作目录根路径
    /// </summary>
    string GetRepositoryRoot();
}

/// <summary>
/// Git集成实现
/// </summary>
public class GitIntegration : IGitIntegration
{
    private readonly ILogger<GitIntegration> _logger;
    private readonly string _workingDirectory;
    private readonly string _gitPath;
    
    public GitIntegration(ILogger<GitIntegration> logger, string workingDirectory)
    {
        _logger = logger;
        _workingDirectory = workingDirectory;
        _gitPath = FindGitPath();
    }
    
    public async Task<GitStatus> GetStatusAsync(CancellationToken ct = default)
    {
        var status = new GitStatus();
        
        try
        {
            // 获取当前分支
            var branchResult = await RunGitCommandAsync("rev-parse --abbrev-ref HEAD", ct);
            status.CurrentBranch = branchResult.Trim();
            
            // 获取状态
            var statusResult = await RunGitCommandAsync("status --porcelain=v1", ct);
            var lines = statusResult.Split('\n', StringSplitOptions.RemoveEmptyEntries);
            
            foreach (var line in lines)
            {
                if (line.Length < 3) continue;
                
                var indexStatus = line[0];
                var workTreeStatus = line[1];
                var file = line.Substring(3).Trim();
                
                if (indexStatus == '?' && workTreeStatus == '?')
                {
                    status.UntrackedFiles.Add(file);
                }
                else if (indexStatus != ' ' && indexStatus != '?')
                {
                    status.StagedFiles.Add(file);
                }
                
                var changeType = workTreeStatus switch
                {
                    'M' => GitChangeType.Modified,
                    'D' => GitChangeType.Deleted,
                    'A' => GitChangeType.Added,
                    'R' => GitChangeType.Renamed,
                    'C' => GitChangeType.Copied,
                    _ => GitChangeType.Modified
                };
                
                status.Changes.Add(new GitChange { Path = file, ChangeType = changeType });
            }
            
            // 获取ahead/behind (对 upstream 引用: branch@{upstream}; 无 upstream 时跳过)
            try
            {
                var tracking = await RunGitCommandAsync(
                    $"rev-list --left-right --count {status.CurrentBranch}...{{upstream}}", ct);
                var parts = tracking.Split('\t');
                if (parts.Length == 2)
                {
                    if (int.TryParse(parts[0], out var ahead)) status.Ahead = ahead;
                    if (int.TryParse(parts[1], out var behind)) status.Behind = behind;
                }
            }
            catch (InvalidOperationException)
            {
                // 无上游分支: ahead/behind 保持 0
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get git status");
        }
        
        return status;
    }
    
    public async Task<List<GitBranch>> GetBranchesAsync(CancellationToken ct = default)
    {
        var branches = new List<GitBranch>();
        
        try
        {
            var result = await RunGitCommandAsync("branch -a", ct);
            var lines = result.Split('\n', StringSplitOptions.RemoveEmptyEntries);
            
            foreach (var line in lines)
            {
                var branchName = line.TrimStart('*', ' ', '\t');
                var isCurrent = line.StartsWith('*');
                
                branches.Add(new GitBranch
                {
                    Name = branchName,
                    IsCurrent = isCurrent
                });
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get branches");
        }
        
        return branches;
    }
    
    public async Task<GitOperationResult> CreateBranchAsync(string branchName, bool checkout = true, CancellationToken ct = default)
    {
        try
        {
            if (checkout)
            {
                var result = await RunGitCommandAsync($"checkout -b {branchName}", ct);
                return new GitOperationResult { Success = true, Output = result };
            }
            else
            {
                var result = await RunGitCommandAsync($"branch {branchName}", ct);
                return new GitOperationResult { Success = true, Output = result };
            }
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message };
        }
    }
    
    public async Task<GitOperationResult> CheckoutAsync(string branchName, CancellationToken ct = default)
    {
        try
        {
            var result = await RunGitCommandAsync($"checkout {branchName}", ct);
            return new GitOperationResult { Success = true, Output = result };
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message };
        }
    }
    
    public async Task<GitOperationResult> StageAsync(string? path = null, CancellationToken ct = default)
    {
        try
        {
            var args = string.IsNullOrEmpty(path) ? "add ." : $"add {path}";
            var result = await RunGitCommandAsync(args, ct);
            return new GitOperationResult { Success = true, Output = result };
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message };
        }
    }
    
    public async Task<GitOperationResult> UnstageAsync(string path, CancellationToken ct = default)
    {
        try
        {
            var result = await RunGitCommandAsync($"reset HEAD {path}", ct);
            return new GitOperationResult { Success = true, Output = result };
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message };
        }
    }
    
    public async Task<GitOperationResult> CommitAsync(string message, CancellationToken ct = default)
    {
        try
        {
            var result = await RunGitCommandAsync($"commit -m \"{message}\"", ct);
            return new GitOperationResult { Success = true, Output = result };
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message };
        }
    }
    
    public async Task<List<GitCommit>> GetLogAsync(int count = 50, CancellationToken ct = default)
    {
        var commits = new List<GitCommit>();
        
        try
        {
            var result = await RunGitCommandAsync($"log -{count} --pretty=format:\"%H|%s|%an|%ai\"", ct);
            var lines = result.Split('\n', StringSplitOptions.RemoveEmptyEntries);
            
            foreach (var line in lines)
            {
                var parts = line.Split('|');
                if (parts.Length >= 4)
                {
                    commits.Add(new GitCommit
                    {
                        Hash = parts[0],
                        Message = parts[1],
                        Author = parts[2],
                        Date = DateTime.Parse(parts[3])
                    });
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get git log");
        }
        
        return commits;
    }
    
    public async Task<string> GetDiffAsync(string? path = null, bool staged = false, CancellationToken ct = default)
    {
        try
        {
            var args = staged ? "diff --cached" : "diff";
            if (!string.IsNullOrEmpty(path))
            {
                args += $" {path}";
            }
            
            return await RunGitCommandAsync(args, ct);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get diff");
            return string.Empty;
        }
    }
    
    public async Task<GitOperationResult> PullAsync(CancellationToken ct = default)
    {
        try
        {
            var result = await RunGitCommandAsync("pull", ct);
            return new GitOperationResult { Success = true, Output = result };
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message };
        }
    }
    
    public async Task<GitOperationResult> PushAsync(CancellationToken ct = default)
    {
        try
        {
            var result = await RunGitCommandAsync("push", ct);
            return new GitOperationResult { Success = true, Output = result };
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message };
        }
    }
    
    public async Task<GitOperationResult> MergeAsync(string branchName, CancellationToken ct = default)
    {
        try
        {
            var result = await RunGitCommandAsync($"merge {branchName}", ct);
            return new GitOperationResult { Success = true, Output = result };
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message };
        }
    }
    
    public async Task<GitOperationResult> RestoreAsync(string path, CancellationToken ct = default)
    {
        try
        {
            var result = await RunGitCommandAsync($"restore {path}", ct);
            return new GitOperationResult { Success = true, Output = result };
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message };
        }
    }
    
    public async Task<GitOperationResult> StageFileAsync(string path, CancellationToken ct = default)
    {
        try
        {
            var result = await RunGitCommandAsync($"add {path}", ct);
            return new GitOperationResult { Success = true, Output = result, FilePath = path };
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message, FilePath = path };
        }
    }
    
    public async Task<GitOperationResult> DiscardAsync(string path, CancellationToken ct = default)
    {
        try
        {
            var result = await RunGitCommandAsync($"checkout -- {path}", ct);
            return new GitOperationResult { Success = true, Output = result, FilePath = path };
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message, FilePath = path };
        }
    }
    
    public async Task<GitOperationResult> CreateCommitAsync(string message, string? description = null, CancellationToken ct = default)
    {
        try
        {
            var commitMessage = string.IsNullOrEmpty(description) 
                ? message 
                : $"{message}\n\n{description}";
            
            var result = await RunGitCommandAsync($"commit -m \"{commitMessage.Replace("\"", "\\\"")}\"", ct);
            return new GitOperationResult { Success = true, Output = result };
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message };
        }
    }
    
    public async Task<GitOperationResult> AddAllAsync(CancellationToken ct = default)
    {
        try
        {
            var result = await RunGitCommandAsync("add -A", ct);
            return new GitOperationResult { Success = true, Output = result };
        }
        catch (Exception ex)
        {
            return new GitOperationResult { Success = false, Error = ex.Message };
        }
    }
    
    public string GetRepositoryRoot()
    {
        return _workingDirectory;
    }
    
    private async Task<string> RunGitCommandAsync(string arguments, CancellationToken ct)
    {
        var process = new System.Diagnostics.Process
        {
            StartInfo = new System.Diagnostics.ProcessStartInfo
            {
                FileName = _gitPath,
                Arguments = arguments,
                WorkingDirectory = _workingDirectory,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            }
        };
        
        process.Start();
        var output = await process.StandardOutput.ReadToEndAsync(ct);
        var error = await process.StandardError.ReadToEndAsync(ct);
        
        await process.WaitForExitAsync(ct);
        
        if (process.ExitCode != 0 && !string.IsNullOrEmpty(error))
        {
            throw new InvalidOperationException($"Git command failed: {error}");
        }
        
        return output;
    }
    
    private string FindGitPath()
    {
        // 尝试常见路径
        var possiblePaths = new[]
        {
            "git",
            "/usr/bin/git",
            "/usr/local/bin/git",
            @"C:\Program Files\Git\cmd\git.exe",
            @"C:\Program Files (x86)\Git\cmd\git.exe"
        };
        
        foreach (var path in possiblePaths)
        {
            try
            {
                var process = new System.Diagnostics.Process
                {
                    StartInfo = new System.Diagnostics.ProcessStartInfo
                    {
                        FileName = path,
                        Arguments = "--version",
                        RedirectStandardOutput = true,
                        UseShellExecute = false,
                        CreateNoWindow = true
                    }
                };
                
                process.Start();
                process.WaitForExit(1000);
                
                if (process.ExitCode == 0)
                {
                    return path;
                }
            }
            catch { }
        }
        
        return "git"; // 默认使用PATH中的git
    }
}
