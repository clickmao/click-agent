using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.search;


public class BochaWebPages
{
    [JsonPropertyName("value")]
    public List<BochaPage>? Value { get; set; }
}
