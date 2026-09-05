using System.Text.Json.Serialization;

namespace agent.userinteraction;

/// <summary>审计条目 (JSONL 一行): 记录每次问询由谁回答、是否批准。</summary>
public class PromptAuditEntry
{
    [JsonPropertyName("ts")]
    public DateTime TimestampUtc { get; set; } = DateTime.UtcNow;

    [JsonPropertyName("kind")]
    public string Kind { get; set; } = string.Empty;

    [JsonPropertyName("service")]
    public string Service { get; set; } = string.Empty;

    [JsonPropertyName("answeredBy")]
    public string AnsweredBy { get; set; } = string.Empty;

    [JsonPropertyName("approved")]
    public bool? Approved { get; set; }

    [JsonPropertyName("detail")]
    public string Detail { get; set; } = string.Empty;
}
