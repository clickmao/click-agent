using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent;

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
