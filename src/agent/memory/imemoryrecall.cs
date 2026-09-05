using agent.rag;

namespace agent.memory;

/// <summary>
/// 记忆召回接口
/// </summary>
public interface IMemoryRecall
{
    /// <summary>
    /// 召回相关记忆
    /// </summary>
    Task<List<MemoryEntry>> RecallAsync(string query, int topK = 5);
    
    /// <summary>
    /// 召回相关记忆（带过滤器）
    /// </summary>
    Task<List<MemoryEntry>> RecallAsync(RecallRequest request);
}

/// <summary>
/// 使用 RAGRecall 实现的记忆召回
/// </summary>
public class MemoryRecall : IMemoryRecall
{
    private readonly IRAGRecall _ragRecall;
    private readonly IAgentMemoryStore _memoryStore;
    
    public MemoryRecall(IRAGRecall ragRecall, IAgentMemoryStore memoryStore)
    {
        _ragRecall = ragRecall;
        _memoryStore = memoryStore;
    }
    
    public async Task<List<MemoryEntry>> RecallAsync(string query, int topK = 5)
    {
        return await RecallAsync(new RecallRequest
        {
            Query = query,
            TopK = topK
        });
    }
    
    public async Task<List<MemoryEntry>> RecallAsync(RecallRequest request)
    {
        var results = await _ragRecall.RecallAsync(request);
        
        var entries = new List<MemoryEntry>();
        foreach (var result in results)
        {
            var entry = await _memoryStore.GetAsync(result.Document.Id);
            if (entry != null)
            {
                entries.Add(entry);
            }
        }
        
        return entries;
    }
}

/// <summary>
/// Agent 记忆存储接口
/// </summary>
public interface IAgentMemoryStore
{
    Task<MemoryEntry?> GetAsync(string id, CancellationToken ct = default);
    Task StoreAsync(MemoryEntry entry, CancellationToken ct = default);
}
