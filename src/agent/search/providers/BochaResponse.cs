using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.search;


public class BochaResponse
{
    [JsonPropertyName("code")]
    public int Code { get; set; }

    [JsonPropertyName("log_id")]
    public string? LogId { get; set; }

    [JsonPropertyName("data")]
    public BochaData? Data { get; set; }
}
