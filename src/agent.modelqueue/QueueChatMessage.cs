using System.Text.Json.Serialization;

namespace agent.modelqueue;


public sealed class QueueChatMessage
{
    [JsonPropertyName("role")]
    public string Role { get; set; } = "user";

    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;

    /// <summary>v0.12.0 A2: 多段 content (text + image_url) — 非空时序列化为数组形态。</summary>
    [JsonIgnore]
    public List<QueueContentPart>? ContentParts { get; set; }

    /// <summary>R456 回灌: assistant 消息携带的 tool_calls (手写 writer 输出; source-gen 不参与)。</summary>
    [JsonIgnore]
    public List<ActionToolCall>? ToolCalls { get; set; }

    /// <summary>R456 回灌: role=tool 消息对应的 tool_call_id。</summary>
    [JsonIgnore]
    public string? ToolCallId { get; set; }

    [JsonIgnore]
    public bool HasParts => ContentParts is { Count: > 0 };

    [JsonIgnore]
    public bool HasToolPayload => (ToolCalls is { Count: > 0 }) || !string.IsNullOrEmpty(ToolCallId);
}
