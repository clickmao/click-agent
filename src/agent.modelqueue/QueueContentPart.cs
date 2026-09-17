using System.Text.Json.Serialization;

namespace agent.modelqueue;


/// <summary>v0.12.0 A2: content part (text | image_url)</summary>
public sealed class QueueContentPart
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = "text";

    [JsonPropertyName("text")]
    public string? Text { get; set; }

    [JsonPropertyName("image_url")]
    public QueueImageUrl? ImageUrl { get; set; }
}
