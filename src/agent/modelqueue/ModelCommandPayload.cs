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
}

/// <summary>模型队列载荷序列化上下文 (AOT: 无反射)</summary>
[System.Text.Json.Serialization.JsonSerializable(typeof(ModelCommandPayload))]
[System.Text.Json.Serialization.JsonSourceGenerationOptions(
    DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull)]
public partial class ModelCommandJsonContext : System.Text.Json.Serialization.JsonSerializerContext
{
}
