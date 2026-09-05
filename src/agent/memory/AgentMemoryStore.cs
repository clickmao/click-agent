using Microsoft.Extensions.Logging;

namespace agent.memory;

/// <summary>
/// Agent 记忆存储实现
/// </summary>
public class AgentMemoryStore : IAgentMemoryStore
{
    private readonly ILogger<AgentMemoryStore> _logger;
    private readonly Dictionary<string, MemoryEntry> _store = new();
    private readonly object _lock = new();
    
    public AgentMemoryStore(ILogger<AgentMemoryStore> logger)
    {
        _logger = logger;
    }
    
    public Task<MemoryEntry?> GetAsync(string id, CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (_store.TryGetValue(id, out var entry))
            {
                entry.AccessCount++;
                entry.LastAccessedAt = DateTime.UtcNow;
                return Task.FromResult<MemoryEntry?>(entry);
            }
        }
        
        return Task.FromResult<MemoryEntry?>(null);
    }
    
    public Task StoreAsync(MemoryEntry entry, CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (string.IsNullOrEmpty(entry.Id))
            {
                entry.Id = Guid.NewGuid().ToString();
            }
            
            entry.LastAccessedAt = DateTime.UtcNow;
            _store[entry.Id] = entry;
        }
        
        _logger.LogDebug("Stored memory entry {EntryId}", entry.Id);
        return Task.CompletedTask;
    }
}
