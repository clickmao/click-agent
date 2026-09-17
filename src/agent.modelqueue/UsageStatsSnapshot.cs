using System.Collections.Concurrent;
using System.Globalization;

namespace agent.modelqueue;


/// <summary>用量统计快照</summary>
public sealed record UsageStatsSnapshot(
    long TotalTokens,
    Dictionary<string, long> TokensByModel,
    Dictionary<string, long> TokensByProvider,
    Dictionary<string, BalanceSnapshot> Balances,
    double EstimatedCostUsd);
