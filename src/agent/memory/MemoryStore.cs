using Microsoft.Extensions.Logging;

namespace agent.memory;

/// <summary>
/// 记忆存储实现（内存版，实现 IMemoryStore 接口）
/// 组合了短期/长期两层：默认写入短期层，标记为 LongTerm 的写入长期层
/// </summary>
public class MemoryStore : IMemoryStore
{
    private readonly ILogger<MemoryStore> _logger;
    private readonly Dictionary<string, MemoryEntry> _entries = new();
    private readonly object _lock = new();

    private const int MaxEntries = 20000;

    public MemoryStore(ILogger<MemoryStore> logger)
    {
        _logger = logger;
    }

    public Task<string> StoreAsync(MemoryEntry entry, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            // 容量淘汰：超过上限时删除最旧的短期记忆
            if (_entries.Count >= MaxEntries)
            {
                var oldest = _entries.Values
                    .Where(e => e.MemoryType == MemoryType.ShortTerm)
                    .OrderBy(e => e.CreatedAt)
                    .FirstOrDefault();

                if (oldest != null)
                {
                    _entries.Remove(oldest.Id);
                }
            }

            _entries[entry.Id] = entry;
        }

        _logger.LogDebug("Stored memory entry {EntryId} of type {Type}", entry.Id, entry.MemoryType);
        return Task.FromResult(entry.Id);
    }

    public Task<MemoryEntry?> GetAsync(string id, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            _entries.TryGetValue(id, out var entry);
            if (entry != null)
            {
                entry.AccessCount++;
                entry.LastAccessedAt = DateTime.UtcNow;
            }
            return Task.FromResult(entry);
        }
    }

    public Task<IReadOnlyList<MemoryEntry>> SearchAsync(string query, int maxResults = 10, CancellationToken cancellationToken = default)
    {
        var queryLower = query.ToLowerInvariant();

        lock (_lock)
        {
            var results = _entries.Values
                .Where(e =>
                    e.Content.ToLowerInvariant().Contains(queryLower) ||
                    e.Tags.Any(t => t.ToLowerInvariant().Contains(queryLower)) ||
                    (e.Summary != null && e.Summary.ToLowerInvariant().Contains(queryLower)))
                .OrderByDescending(e => e.Importance)
                .ThenByDescending(e => e.CreatedAt)
                .Take(maxResults)
                .ToList();

            return Task.FromResult<IReadOnlyList<MemoryEntry>>(results);
        }
    }

    public Task UpdateAsync(MemoryEntry entry, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            if (_entries.ContainsKey(entry.Id))
            {
                entry.UpdatedAt = DateTime.UtcNow;
                _entries[entry.Id] = entry;
            }
            else
            {
                _logger.LogWarning("Attempted to update non-existent memory entry {EntryId}", entry.Id);
            }
        }

        return Task.CompletedTask;
    }

    public Task DeleteAsync(string id, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            _entries.Remove(id);
        }

        return Task.CompletedTask;
    }

    public Task<IReadOnlyList<MemoryEntry>> GetRecentAsync(int count = 10, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            var results = _entries.Values
                .OrderByDescending(e => e.CreatedAt)
                .Take(count)
                .ToList();

            return Task.FromResult<IReadOnlyList<MemoryEntry>>(results);
        }
    }

    public Task<IReadOnlyList<MemoryEntry>> GetBySessionAsync(string sessionId, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            var results = _entries.Values
                .Where(e => e.SessionId == sessionId)
                .OrderBy(e => e.CreatedAt)
                .ToList();

            return Task.FromResult<IReadOnlyList<MemoryEntry>>(results);
        }
    }

    public Task ClearSessionAsync(string sessionId, CancellationToken cancellationToken = default)
    {
        lock (_lock)
        {
            var toRemove = _entries.Values
                .Where(e => e.SessionId == sessionId)
                .Select(e => e.Id)
                .ToList();

            foreach (var id in toRemove)
            {
                _entries.Remove(id);
            }
        }

        _logger.LogDebug("Cleared all memory entries for session {SessionId}", sessionId);
        return Task.CompletedTask;
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
                ThisSessionCount: entries.Count(e => e.SessionId != string.Empty),
                TotalTokens: entries.Sum(e => e.TokenCount));

            return Task.FromResult(stats);
        }
    }
}
