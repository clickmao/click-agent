using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent;


/// <summary>
/// v0.12.0 (Workstream A1) 多模态 content 双形态 DTO — 计划 R2 §1。
/// 纯文本保持 string (向后兼容, 现有链路零改动); 图像理解时 ContentParts 序列化为多段数组。
/// AOT 安全: 显式 DTO + 手写 converter (禁反射)。
/// </summary>
[JsonConverter(typeof(OpenAIChatMessageConverter))]
public sealed class OpenAIMultimodalMessage
{
    [JsonPropertyName("role")]
    public string Role { get; set; } = string.Empty;

    /// <summary>纯文本形态 (与 ContentParts 互斥: 有 Parts 时序列化忽略本字段)。</summary>
    [JsonPropertyName("content")]
    public string? Content { get; set; }

    /// <summary>多段形态: [{"type":"text",...},{"type":"image_url",...}]</summary>
    [JsonIgnore]
    public List<ContentPart>? ContentParts { get; set; }

    public bool HasParts => ContentParts is { Count: > 0 };

    public static OpenAIMultimodalMessage Text(string role, string text) =>
        new() { Role = role, Content = text };

    public static OpenAIMultimodalMessage WithImage(string role, string text, string imageUrl) =>
        new()
        {
            Role = role,
            ContentParts = new List<ContentPart>
            {
                new() { Type = "text", Text = text },
                new() { Type = "image_url", ImageUrl = new ImageUrlSpec { Url = imageUrl } },
            },
        };
}
