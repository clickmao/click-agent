using Microsoft.Extensions.Logging;

namespace agent.workspace;


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
