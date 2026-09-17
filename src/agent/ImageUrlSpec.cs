using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent;


public sealed class ImageUrlSpec
{
    [JsonPropertyName("url")]
    public string Url { get; set; } = string.Empty;
}
