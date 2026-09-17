using agent.core;

namespace agent.memory;


/// <summary>
/// 记忆统计
/// </summary>
public record MemoryStatistics(
    int TotalEntries,
    int ShortTermCount,
    int LongTermCount,
    int ThisSessionCount,
    long TotalTokens);
