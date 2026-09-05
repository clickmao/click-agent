namespace agent.memory;

/// <summary>
/// 长期记忆实现
/// </summary>
public class LongTermMemory : IMemoryStore
{
    private readonly Dictionary<string, MemoryEntry> _entries = new();
    private readonly Dictionary<string, List<string>> _sessionIndex = new();
    private readonly object _lock = new();
    
    private const int MaxLongTermEntries = 10000;
    
    public async Task<string> StoreAsync(MemoryEntry entry, CancellationToken cancellationToken = default)
    {
        await Task.Run(() =>
        {
            lock (_lock)
            {
                _entries[entry.Id] = entry;
                
                if (!_sessionIndex.ContainsKey(entry.SessionId))
                {
                    _sessionIndex[entry.SessionId] = new List<string>();
                }
                _sessionIndex[entry.SessionId].Add(entry.Id);
                
                // 简单的记忆淘汰策略：当超过最大容量时，删除最老的记忆
                if (_entries.Count > MaxLongTermEntries)
                {
                    var oldest = _entries.Values
                        .Where(e => e.MemoryType == MemoryType.LongTerm)
                        .OrderBy(e => e.CreatedAt)
                        .FirstOrDefault();
                    
                    if (oldest != null)
                    {
                        _entries.Remove(oldest.Id);
                    }
                }
            }
        }, cancellationToken);
        
        return entry.Id;
    }
    
    public Task<MemoryEntry?> GetAsync(string id, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            _entries.TryGetValue(id, out var entry);
            return Task.FromResult(entry);
        }
    }
    
    public async Task<IReadOnlyList<MemoryEntry>> SearchAsync(string query, int maxResults = 10, CancellationToken cancellationToken = default)
    {
        var queryLower = query.ToLowerInvariant();
        
        return await Task.Run(() =>
        {
            lock (_lock)
            {
                var results = _entries.Values
                    .Where(e => e.MemoryType == MemoryType.LongTerm)
                    .Where(e => 
                        e.Content.ToLowerInvariant().Contains(queryLower) ||
                        e.Tags.Any(t => t.ToLowerInvariant().Contains(queryLower)))
                    .OrderByDescending(e => e.Importance * (1.0 / (DateTime.UtcNow - e.CreatedAt).TotalDays + 1))
                    .Take(maxResults)
                    .ToList();
                
                return (IReadOnlyList<MemoryEntry>)results;
            }
        }, cancellationToken);
    }
    
    public async Task UpdateAsync(MemoryEntry entry, CancellationToken cancellationToken = default)
    {
        await Task.Run(() =>
        {
            lock (_lock)
            {
                if (_entries.ContainsKey(entry.Id))
                {
                    entry.UpdatedAt = DateTime.UtcNow;
                    _entries[entry.Id] = entry;
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
                if (_entries.Remove(id))
                {
                    foreach (var sessionList in _sessionIndex.Values)
                    {
                        sessionList.Remove(id);
                    }
                }
            }
        }, cancellationToken);
    }
    
    public async Task<IReadOnlyList<MemoryEntry>> GetRecentAsync(int count = 10, CancellationToken cancellationToken = default)
    {
        return await Task.Run(() =>
        {
            lock (_lock)
            {
                return (IReadOnlyList<MemoryEntry>)_entries.Values
                    .Where(e => e.MemoryType == MemoryType.LongTerm)
                    .OrderByDescending(e => e.CreatedAt)
                    .Take(count)
                    .ToList();
            }
        }, cancellationToken);
    }
    
    public Task<IReadOnlyList<MemoryEntry>> GetBySessionAsync(string sessionId, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            if (!_sessionIndex.TryGetValue(sessionId, out var ids))
            {
                return Task.FromResult<IReadOnlyList<MemoryEntry>>(Array.Empty<MemoryEntry>());
            }
            
            var entries = ids
                .Where(id => _entries.ContainsKey(id))
                .Select(id => _entries[id])
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
                if (_sessionIndex.TryGetValue(sessionId, out var ids))
                {
                    foreach (var id in ids)
                    {
                        _entries.Remove(id);
                    }
                    _sessionIndex.Remove(sessionId);
                }
            }
        }, cancellationToken);
    }
    
    public Task<MemoryStatistics> GetStatisticsAsync(CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            var entries = _entries.Values.ToList();
            var stats = new MemoryStatistics(
                TotalEntries: entries.Count,
                ShortTermCount: entries.Count(e => e.MemoryType == MemoryType.ShortTerm),
                LongTermCount: entries.Count(e => e.MemoryType == MemoryType.LongTerm),
                ThisSessionCount: 0,
                TotalTokens: entries.Sum(e => e.TokenCount)
            );
            
            return Task.FromResult(stats);
        }
    }
}
