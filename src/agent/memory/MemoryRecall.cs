using agent.rag;

namespace agent.memory;


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
