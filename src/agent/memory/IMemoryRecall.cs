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
