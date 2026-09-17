using System.Text.Json.Serialization;

namespace agent;


/// <summary>/token stats 载荷 (v0.10.0: 用量统计 + 余额快照 + 余额不足 flags)</summary>
public sealed class TokenStatsPayload
{
    public string Command { get; set; } = string.Empty;
    public bool Ok { get; set; }
    public long TotalTokens { get; set; }
    public Dictionary<string, long>? TokensByModel { get; set; }
    public Dictionary<string, long>? TokensByProvider { get; set; }
    public double EstimatedCostUsd { get; set; }
    public Dictionary<string, BalanceEntryPayload>? Balances { get; set; }
    /// <summary>最近一次余额不足提示 (model:xxx flags:余额不足 协议行)</summary>
    public string? BalanceFlag { get; set; }
}
