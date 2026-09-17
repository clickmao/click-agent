using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.search;


// ── 博查协议模型 (source-gen 序列化, AOT 兼容) ──

public class BochaRequest
{
    [JsonPropertyName("query")]
    public string Query { get; set; } = string.Empty;

    [JsonPropertyName("summary")]
    public bool Summary { get; set; }

    [JsonPropertyName("freshness")]
    public string Freshness { get; set; } = "noLimit";

    [JsonPropertyName("count")]
    public int Count { get; set; } = 10;
}
