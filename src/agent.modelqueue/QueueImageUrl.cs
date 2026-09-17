using System.Text.Json.Serialization;

namespace agent.modelqueue;


public sealed class QueueImageUrl
{
    [JsonPropertyName("url")]
    public string Url { get; set; } = string.Empty;
}
