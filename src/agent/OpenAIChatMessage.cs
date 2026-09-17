using Microsoft.Extensions.Logging;
using agent.core;
using agent.workspace;
using agent.codegen;
using agent.recovery;
using agent.vectormemory;
using agent.memory;
using agent.templates;
using agent.search;
using agent.session;
using agent.context;
using agent.rag;
using agent.tendency;
using agent.tokencompression;
using agent.registry;

using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text;

using agent.intent;

namespace agent;


[JsonConverter(typeof(agent.ChatMessagePartsConverter))]
public sealed class OpenAIChatMessage
{
    [JsonPropertyName("role")]
    public string Role { get; set; } = string.Empty;

    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;

    /// <summary>
    /// v0.12.0 A2: 图像附件 (image_url/base64 data URL) — 非空时该消息序列化为 parts[] 多段形态
    /// (由 VisionJsonContext + OpenAIMultimodalMessage 承担, 本字段不直接序列化)。
    /// </summary>
    [JsonIgnore]
    public List<string>? ImageUrls { get; set; }

    [JsonIgnore]
    public bool HasImages => ImageUrls is { Count: > 0 };
}
