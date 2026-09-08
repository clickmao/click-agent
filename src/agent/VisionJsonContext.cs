using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent;

/// <summary>
/// v0.12.0 A2 — 视觉请求 source-gen 上下文 (OpenAIChatRequest 带图路径:
/// messages 序列化为 content parts[], 由 OpenAIChatMessageConverter 承担)。
/// </summary>
[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
[JsonSerializable(typeof(OpenAIChatRequest))]
internal partial class VisionJsonContext : JsonSerializerContext
{
}

public static partial class VisionChatHelper
{
    /// <summary>本地图 → base64 data URL (png/jpg/jpeg/webp; >4MB 拒绝)。</summary>
    public static string ToDataUrl(string localPath)
    {
        if (!File.Exists(localPath))
            throw new FileNotFoundException($"图像附件不存在: {localPath}");
        var bytes = File.ReadAllBytes(localPath);
        if (bytes.Length > 4 * 1024 * 1024)
            throw new InvalidOperationException($"图像超过 4MB 上限: {bytes.Length}B ({localPath})");
        var ext = Path.GetExtension(localPath).ToLowerInvariant() switch
        {
            ".png" => "image/png",
            ".jpg" or ".jpeg" => "image/jpeg",
            ".webp" => "image/webp",
            _ => "image/png",
        };
        return $"data:{ext};base64,{Convert.ToBase64String(bytes)}";
    }
}

/// <summary>
/// OpenAIChatMessage 双形态 converter (string | parts[]) — AOT 安全手写。
/// 与 OpenAIMultimodalMessage converter 同逻辑, 适配 OpenAIChatMessage (Content string + ImageUrls)。
/// </summary>
public sealed class ChatMessagePartsConverter : JsonConverter<OpenAIChatMessage>
{
    public override OpenAIChatMessage Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        var msg = new OpenAIChatMessage();
        using var doc = JsonDocument.ParseValue(ref reader);
        var root = doc.RootElement;
        if (root.TryGetProperty("role", out var role))
            msg.Role = role.GetString() ?? string.Empty;
        if (root.TryGetProperty("content", out var content))
        {
            if (content.ValueKind == JsonValueKind.String)
                msg.Content = content.GetString() ?? string.Empty;
            // parts[] 形态读回: 拼接 text 部分 (响应解析用不到图, 保守拼接)
            else if (content.ValueKind == JsonValueKind.Array)
            {
                var sb = new System.Text.StringBuilder();
                foreach (var el in content.EnumerateArray())
                    if (el.TryGetProperty("text", out var txt))
                        sb.Append(txt.GetString());
                msg.Content = sb.ToString();
            }
        }
        return msg;
    }

    public override void Write(Utf8JsonWriter writer, OpenAIChatMessage value, JsonSerializerOptions options)
    {
        writer.WriteStartObject();
        writer.WriteString("role", value.Role);
        if (value.HasImages)
        {
            writer.WritePropertyName("content");
            writer.WriteStartArray();
            // 文本段在前
            writer.WriteStartObject();
            writer.WriteString("type", "text");
            writer.WriteString("text", value.Content ?? string.Empty);
            writer.WriteEndObject();
            foreach (var url in value.ImageUrls!)
            {
                writer.WriteStartObject();
                writer.WriteString("type", "image_url");
                writer.WritePropertyName("image_url");
                writer.WriteStartObject();
                writer.WriteString("url", url);
                writer.WriteEndObject();
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
