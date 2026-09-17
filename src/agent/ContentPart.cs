using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent;


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
