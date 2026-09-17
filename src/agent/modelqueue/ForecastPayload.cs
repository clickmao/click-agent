using System.Text.Json.Serialization;

namespace agent;


/// <summary>/forecast 载荷 (v0.10.0 新需求4: 下轮预估读回 — v7.11 机制前端可见化)</summary>
public sealed class ForecastPayload
{
    public string AgentUid { get; set; } = string.Empty;
    public string TaskSummary { get; set; } = string.Empty;
    public string LastIntent { get; set; } = string.Empty;
    public string Tendency { get; set; } = string.Empty;
    public string ContinuationHint { get; set; } = string.Empty;
    public bool LikelyContinues { get; set; }
    public int TurnCount { get; set; }
    public DateTime UpdatedAt { get; set; }
}
