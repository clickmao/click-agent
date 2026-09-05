using agent.core;

namespace agent.memory;

/// <summary>
/// 记忆存储接口
/// </summary>
public interface IMemoryStore
{
    /// <summary>
    /// 存储新的记忆
    /// </summary>
    Task<string> StoreAsync(MemoryEntry entry, CancellationToken cancellationToken = default);
    
    /// <summary>
    /// 根据ID获取记忆
    /// </summary>
    Task<MemoryEntry?> GetAsync(string id, CancellationToken cancellationToken = default);
    
    /// <summary>
    /// 搜索相关记忆
    /// </summary>
    Task<IReadOnlyList<MemoryEntry>> SearchAsync(string query, int maxResults = 10, CancellationToken cancellationToken = default);
    
    /// <summary>
    /// 更新记忆
    /// </summary>
    Task UpdateAsync(MemoryEntry entry, CancellationToken cancellationToken = default);
    
    /// <summary>
    /// 删除记忆
    /// </summary>
    Task DeleteAsync(string id, CancellationToken cancellationToken = default);
    
    /// <summary>
    /// 获取最近的记忆
    /// </summary>
    Task<IReadOnlyList<MemoryEntry>> GetRecentAsync(int count = 10, CancellationToken cancellationToken = default);
    
    /// <summary>
    /// 获取会话的所有记忆
    /// </summary>
    Task<IReadOnlyList<MemoryEntry>> GetBySessionAsync(string sessionId, CancellationToken cancellationToken = default);
    
    /// <summary>
    /// 清空会话记忆
    /// </summary>
    Task ClearSessionAsync(string sessionId, CancellationToken cancellationToken = default);
    
    /// <summary>
    /// 获取记忆统计
    /// </summary>
    Task<MemoryStatistics> GetStatisticsAsync(CancellationToken cancellationToken = default);
}

/// <summary>
/// 记忆统计
/// </summary>
public record MemoryStatistics(
    int TotalEntries,
    int ShortTermCount,
    int LongTermCount,
    int ThisSessionCount,
    long TotalTokens);
