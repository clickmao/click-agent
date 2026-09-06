using System.Text.Json.Serialization;

namespace agent;

/// <summary>模型队列指令 JSON 载荷 (v7.15: /model 与 /balance 输出 — source-gen AOT fast-path 铁律)</summary>
public sealed class ModelCommandPayload
{
    public string Command { get; set; } = string.Empty;
    public bool Ok { get; set; }
    public string? Active { get; set; }
    public string? Provider { get; set; }
    public int ReasoningScore { get; set; }
    public int CodingScore { get; set; }
    public string? LastSelection { get; set; }
    public int Switches { get; set; }
    public string? Target { get; set; }
    public int HttpStatusCode { get; set; }
    public string? Verdict { get; set; }
    public double? TotalGranted { get; set; }
    public double? TotalUsed { get; set; }
    public double? TotalRemaining { get; set; }
    public string? Error { get; set; }
    public string? Note { get; set; }

    /// <summary>需求1: 官方通道 key 是否已注入 (true/false — 不回显 key 本身)</summary>
    public bool? OfficialKeyPresent { get; set; }

    /// <summary>/model list: 可用模型条目 (序号 1-N, 序号可直接用于 /model &lt;序号&gt; 指定)</summary>
    public List<ModelListItem>? Models { get; set; }

    /// <summary>当前执行模式: auto (智能选模, 默认) / manual (用户指定模型)</summary>
    public string? Mode { get; set; }
}

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

/// <summary>余额条目 (provider 级快照)</summary>
public sealed class BalanceEntryPayload
{
    public string Provider { get; set; } = string.Empty;
    public double? Remaining { get; set; }
    public DateTime At { get; set; }
    public bool FromApi { get; set; }
}

/// <summary>/model list 单条模型条目 (序号 = models.yaml 目录顺序)</summary>
public sealed class ModelListItem
{
    /// <summary>序号 (1-N, /model &lt;序号&gt; 即指定该模型)</summary>
    public int Index { get; set; }
    public string Id { get; set; } = string.Empty;
    public string Provider { get; set; } = string.Empty;
    public double PriceInPerM { get; set; }
    public double PriceOutPerM { get; set; }
    public int ReasoningScore { get; set; }
    public int CodingScore { get; set; }
    public int ContextWindow { get; set; }
    public bool IsActive { get; set; }
}

/// <summary>模型队列载荷序列化上下文 (AOT: 无反射)</summary>
[System.Text.Json.Serialization.JsonSerializable(typeof(ModelCommandPayload))]
[System.Text.Json.Serialization.JsonSerializable(typeof(ModelListItem))]
[System.Text.Json.Serialization.JsonSerializable(typeof(TokenStatsPayload))]
[System.Text.Json.Serialization.JsonSerializable(typeof(BalanceEntryPayload))]
[System.Text.Json.Serialization.JsonSerializable(typeof(ForecastPayload))]
[System.Text.Json.Serialization.JsonSourceGenerationOptions(
    DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull)]
public partial class ModelCommandJsonContext : System.Text.Json.Serialization.JsonSerializerContext
{
}
