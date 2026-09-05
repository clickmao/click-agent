namespace agent.datastore;

/// <summary>
/// 数据条目
/// </summary>
public class DataEntry
{
    public string Key { get; set; } = string.Empty;
    public string Value { get; set; } = string.Empty;
    public string? Category { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    public Dictionary<string, object> Metadata { get; set; } = new();
    public List<string> Tags { get; set; } = new();
}

/// <summary>
/// 数据查询
/// </summary>
public class DataQuery
{
    public string? Category { get; set; }
    public List<string>? Tags { get; set; }
    public string? KeyPattern { get; set; }
    public DateTime? FromDate { get; set; }
    public DateTime? ToDate { get; set; }
    public int Skip { get; set; }
    public int Take { get; set; } = 50;
}

/// <summary>
/// 数据存储接口
/// </summary>
public interface IDataStore
{
    Task<DataEntry> SaveAsync(DataEntry entry);
    Task<DataEntry?> GetAsync(string key);
    Task<IEnumerable<DataEntry>> QueryAsync(DataQuery query);
    Task DeleteAsync(string key);
    Task<bool> ExistsAsync(string key);
    Task<IEnumerable<string>> GetCategoriesAsync();
}

/// <summary>
/// 数据存储实现
/// </summary>
public class DataStore : IDataStore
{
    private readonly Dictionary<string, DataEntry> _store = new();
    private readonly object _lock = new();
    
    public Task<DataEntry> SaveAsync(DataEntry entry)
    {
        lock (_lock)
        {
            entry.UpdatedAt = DateTime.UtcNow;
            if (!_store.ContainsKey(entry.Key))
            {
                entry.CreatedAt = DateTime.UtcNow;
            }
            _store[entry.Key] = entry;
        }
        return Task.FromResult(entry);
    }
    
    public Task<DataEntry?> GetAsync(string key)
    {
        lock (_lock)
        {
            _store.TryGetValue(key, out var entry);
            return Task.FromResult(entry);
        }
    }
    
    public Task<IEnumerable<DataEntry>> QueryAsync(DataQuery query)
    {
        lock (_lock)
        {
            var results = _store.Values.AsEnumerable();
            
            if (!string.IsNullOrEmpty(query.Category))
            {
                results = results.Where(e => e.Category == query.Category);
            }
            
            if (query.Tags != null && query.Tags.Any())
            {
                results = results.Where(e => query.Tags.Any(t => e.Tags.Contains(t)));
            }
            
            if (!string.IsNullOrEmpty(query.KeyPattern))
            {
                results = results.Where(e => e.Key.Contains(query.KeyPattern));
            }
            
            if (query.FromDate.HasValue)
            {
                results = results.Where(e => e.CreatedAt >= query.FromDate.Value);
            }
            
            if (query.ToDate.HasValue)
            {
                results = results.Where(e => e.CreatedAt <= query.ToDate.Value);
            }
            
            return Task.FromResult(results.Skip(query.Skip).Take(query.Take));
        }
    }
    
    public Task DeleteAsync(string key)
    {
        lock (_lock)
        {
            _store.Remove(key);
        }
        return Task.CompletedTask;
    }
    
    public Task<bool> ExistsAsync(string key)
    {
        lock (_lock)
        {
            return Task.FromResult(_store.ContainsKey(key));
        }
    }
    
    public Task<IEnumerable<string>> GetCategoriesAsync()
    {
        lock (_lock)
        {
            var categories = _store.Values
                .Where(e => !string.IsNullOrEmpty(e.Category))
                .Select(e => e.Category!)
                .Distinct()
                .OrderBy(c => c);
            
            return Task.FromResult<IEnumerable<string>>(categories.ToList());
        }
    }
}
