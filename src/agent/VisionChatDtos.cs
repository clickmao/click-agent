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

/// <summary>content part (text | image_url 两类 — video/file 待后续 workstream)</summary>
public sealed class ContentPart
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = "text";

    [JsonPropertyName("text")]
    public string? Text { get; set; }

    [JsonPropertyName("image_url")]
    public ImageUrlSpec? ImageUrl { get; set; }
}

public sealed class ImageUrlSpec
{
    [JsonPropertyName("url")]
    public string Url { get; set; } = string.Empty;
}

/// <summary>string | parts[] 双形态序列化 (手写, AOT 安全)。</summary>
public sealed class OpenAIChatMessageConverter : JsonConverter<OpenAIMultimodalMessage>
{
    public override OpenAIMultimodalMessage Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        var msg = new OpenAIMultimodalMessage();
        using var doc = JsonDocument.ParseValue(ref reader);
        var root = doc.RootElement;
        if (root.TryGetProperty("role", out var role))
            msg.Role = role.GetString() ?? string.Empty;
        if (root.TryGetProperty("content", out var content))
        {
            if (content.ValueKind == JsonValueKind.String)
                msg.Content = content.GetString();
            else if (content.ValueKind == JsonValueKind.Array)
            {
                msg.ContentParts = new List<ContentPart>();
                foreach (var el in content.EnumerateArray())
                {
                    var part = new ContentPart { Type = (el.TryGetProperty("type", out var t) ? t.GetString() : "text") ?? "text" };
                    if (el.TryGetProperty("text", out var txt))
                        part.Text = txt.GetString();
                    if (el.TryGetProperty("image_url", out var iu) && iu.TryGetProperty("url", out var u))
                        part.ImageUrl = new ImageUrlSpec { Url = u.GetString() ?? "" };
                    msg.ContentParts.Add(part);
                }
            }
        }
        return msg;
    }

    public override void Write(Utf8JsonWriter writer, OpenAIMultimodalMessage value, JsonSerializerOptions options)
    {
        writer.WriteStartObject();
        writer.WriteString("role", value.Role);
        if (value.HasParts)
        {
            writer.WritePropertyName("content");
            writer.WriteStartArray();
            foreach (var part in value.ContentParts!)
            {
                writer.WriteStartObject();
                writer.WriteString("type", part.Type);
                if (part.Type == "text")
                    writer.WriteString("text", part.Text ?? string.Empty);
                else if (part.Type == "image_url" && part.ImageUrl != null)
                {
                    writer.WritePropertyName("image_url");
                    writer.WriteStartObject();
                    writer.WriteString("url", part.ImageUrl.Url);
                    writer.WriteEndObject();
                }
                writer.WriteEndObject();
            }
            writer.WriteEndArray();
        }
        else
        {
            writer.WriteString("content", value.Content ?? string.Empty);
        }
        writer.WriteEndObject();
    }
}
