using agent.rag;

namespace agent.memory;


/// <summary>
/// Agent 记忆存储接口
/// </summary>
public interface IAgentMemoryStore
{
    Task<MemoryEntry?> GetAsync(string id, CancellationToken ct = default);
    Task StoreAsync(MemoryEntry entry, CancellationToken ct = default);
}
