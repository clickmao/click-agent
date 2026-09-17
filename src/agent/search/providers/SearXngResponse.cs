using System.Net.Http.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.search;


// ── SearXNG JSON 协议模型 ──

public class SearXngResponse
{
    [JsonPropertyName("query")]
    public string? Query { get; set; }

    [JsonPropertyName("results")]
    public List<SearXngResult>? Results { get; set; }

    [JsonPropertyName("number_of_results")]
    public long NumberOfResults { get; set; }
}
