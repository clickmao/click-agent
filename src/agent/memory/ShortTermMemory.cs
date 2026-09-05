namespace agent.memory;

/// <summary>
/// 短期记忆实现
/// </summary>
public class ShortTermMemory : IMemoryStore
{
    private readonly List<MemoryEntry> _entries = new();
    private readonly object _lock = new();
    
    private readonly int _maxCapacity;
    private readonly TimeSpan _expirationTime;
    
    public ShortTermMemory(int maxCapacity = 100, TimeSpan? expirationTime = null)
    {
        _maxCapacity = maxCapacity;
        _expirationTime = expirationTime ?? TimeSpan.FromHours(24);
    }
    
    public async Task<string> StoreAsync(MemoryEntry entry, CancellationToken cancellationToken = default)
    {
        await Task.Run(() =>
        {
            lock (_lock)
            {
                // 设置为短期记忆类型
                entry.MemoryType = MemoryType.ShortTerm;
                entry.ExpiresAt = DateTime.UtcNow.Add(_expirationTime);
                
                _entries.Add(entry);
                
                // 容量超限时删除最老的记忆
                while (_entries.Count > _maxCapacity)
                {
                    _entries.RemoveAt(0);
                }
            }
        }, cancellationToken);
        
        return entry.Id;
    }
    
    public Task<MemoryEntry?> GetAsync(string id, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            CleanExpired();
            var entry = _entries.FirstOrDefault(e => e.Id == id);
            return Task.FromResult(entry);
        }
    }
    
    public async Task<IReadOnlyList<MemoryEntry>> SearchAsync(string query, int maxResults = 10, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            CleanExpired();
            
            var queryLower = query.ToLowerInvariant();
            var results = _entries
                .Where(e => 
                    e.Content.ToLowerInvariant().Contains(queryLower) ||
                    e.Tags.Any(t => t.ToLowerInvariant().Contains(queryLower)))
                .OrderByDescending(e => e.CreatedAt)
                .Take(maxResults)
                .ToList();
            
            return results;
        }
    }
    
    public async Task UpdateAsync(MemoryEntry entry, CancellationToken cancellationToken = default)
    {
        await Task.Run(() =>
        {
            lock (_lock)
            {
                var index = _entries.FindIndex(e => e.Id == entry.Id);
                if (index >= 0)
                {
                    entry.UpdatedAt = DateTime.UtcNow;
                    _entries[index] = entry;
                }
            }
        }, cancellationToken);
    }
    
    public async Task DeleteAsync(string id, CancellationToken cancellationToken = default)
    {
        await Task.Run(() =>
        {
            lock (_lock)
            {
                _entries.RemoveAll(e => e.Id == id);
            }
        }, cancellationToken);
    }
    
    public async Task<IReadOnlyList<MemoryEntry>> GetRecentAsync(int count = 10, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            CleanExpired();
            
            var recent = _entries
                .OrderByDescending(e => e.CreatedAt)
                .Take(count)
                .ToList();
            
            return recent;
        }
    }
    
    public Task<IReadOnlyList<MemoryEntry>> GetBySessionAsync(string sessionId, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            CleanExpired();
            
            var entries = _entries
                .Where(e => e.SessionId == sessionId)
                .OrderByDescending(e => e.CreatedAt)
                .ToList();
            
            return Task.FromResult<IReadOnlyList<MemoryEntry>>(entries);
        }
    }
    
    public async Task ClearSessionAsync(string sessionId, CancellationToken cancellationToken = default)
    {
        await Task.Run(() =>
        {
            lock (_lock)
            {
                _entries.RemoveAll(e => e.SessionId == sessionId);
            }
        }, cancellationToken);
    }
    
    public Task<MemoryStatistics> GetStatisticsAsync(CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            CleanExpired();
            
            var stats = new MemoryStatistics(
                TotalEntries: _entries.Count,
                ShortTermCount: _entries.Count,
                LongTermCount: 0,
                ThisSessionCount: _entries.Count(e => e.SessionId != string.Empty),
                TotalTokens: _entries.Sum(e => e.TokenCount)
            );
            
            return Task.FromResult(stats);
        }
    }
    
    /// <summary>
    /// 清理过期记忆
    /// </summary>
    private void CleanExpired()
    {
        var now = DateTime.UtcNow;
        _entries.RemoveAll(e => e.ExpiresAt.HasValue && e.ExpiresAt.Value < now);
    }
}
