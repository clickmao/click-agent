using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.vectormemory;


/// <summary>
/// 记忆召回器
/// </summary>
public interface IVectorMemoryRecall
{
    Task<List<VectorDocument>> RecallAsync(string query, int topK = 5);
    Task<List<VectorDocument>> RecallByContextAsync(string context, int topK = 5);
    Task<List<VectorDocument>> RecallByKeywordsAsync(List<string> keywords, int topK = 5);
}
