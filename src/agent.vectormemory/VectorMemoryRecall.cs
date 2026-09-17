using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.vectormemory;


/// <summary>
/// 记忆召回器实现
/// </summary>
public class VectorMemoryRecall : IVectorMemoryRecall
{
    private readonly IVectorStore _vectorStore;
    private readonly ILogger<VectorMemoryRecall> _logger;
    
    public VectorMemoryRecall(IVectorStore vectorStore, ILogger<VectorMemoryRecall> logger)
    {
        _vectorStore = vectorStore;
        _logger = logger;
    }
    
    public async Task<List<VectorDocument>> RecallAsync(string query, int topK = 5)
    {
        var request = new SemanticSearchRequest
        {
            Query = query,
            TopK = topK
        };
        
        var results = await _vectorStore.SearchAsync(request);
        return results.Select(r => r.Entry).ToList();
    }
    
    public async Task<List<VectorDocument>> RecallByContextAsync(string context, int topK = 5)
    {
        return await RecallAsync(context, topK);
    }
    
    public async Task<List<VectorDocument>> RecallByKeywordsAsync(List<string> keywords, int topK = 5)
    {
        var request = new SemanticSearchRequest
        {
            Query = string.Join(" ", keywords),
            TopK = topK,
            FilterKeywords = keywords
        };
        
        var results = await _vectorStore.SearchAsync(request);
        return results.Select(r => r.Entry).ToList();
    }
}
