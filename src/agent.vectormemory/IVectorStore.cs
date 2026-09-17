using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.vectormemory;


/// <summary>
/// 向量存储接口
/// </summary>
public interface IVectorStore
{
    /// <summary>
    /// 存储记忆
    /// </summary>
    Task<string> StoreAsync(VectorDocument entry);
    
    /// <summary>
    /// 语义搜索
    /// </summary>
    Task<List<SemanticSearchResult>> SearchAsync(SemanticSearchRequest request);
    
    /// <summary>
    /// 获取记忆
    /// </summary>
    Task<VectorDocument?> GetAsync(string id);
    
    /// <summary>
    /// 更新记忆
    /// </summary>
    Task UpdateAsync(VectorDocument entry);
    
    /// <summary>
    /// 删除记忆
    /// </summary>
    Task DeleteAsync(string id);
    
    /// <summary>
    /// 生成Embedding
    /// </summary>
    Task<float[]?> GenerateEmbeddingAsync(string text);
    
    /// <summary>
    /// 获取相似记忆
    /// </summary>
    Task<List<VectorDocument>> GetSimilarAsync(string id, int topK = 5);
}
