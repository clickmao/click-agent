using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.search;

/// <summary>
/// 博查 BochaAI 搜索插件 (api.bochaai.com/v1/web-search)
/// 国内团队专为 AI 场景做的搜索 API, 中文准确度高, 按次付费。
/// 协议: POST JSON, Bearer Key; 响应 data.webPages.value[] 含 name/url/summary/siteName/datePublished。
/// </summary>
public sealed class BochaSearchProvider : ISearchProvider
{
    private readonly HttpClient _http;
    private readonly ILogger<BochaSearchProvider> _logger;
    private string? _apiKey;

    public string Name => "bocha";
    public bool IsConfigured => !string.IsNullOrWhiteSpace(_apiKey);
    public int DefaultPriority => 20;

    public BochaSearchProvider(HttpClient http, ILogger<BochaSearchProvider> logger, string? apiKey = null)
    {
        _http = http;
        _logger = logger;
        _apiKey = string.IsNullOrWhiteSpace(apiKey) ? null : apiKey.Trim();
    }

    /// <summary>凭据问询后热注入 (免重建插件实例)</summary>
    public void SetApiKey(string apiKey)
    {
        if (!string.IsNullOrWhiteSpace(apiKey))
            _apiKey = apiKey.Trim();
    }

    public async Task<List<SearchResult>> SearchAsync(string query, SearchOptions options, CancellationToken ct)
    {
        if (!IsConfigured)
            throw new InvalidOperationException("博查 API Key 未配置 (Search:Providers:bocha:apiKey)");

        var payload = new BochaRequest
        {
            Query = query,
            Summary = true,
            Freshness = MapFreshness(options),
            Count = Math.Clamp(options.MaxResults, 1, 50),
        };

        using var request = new HttpRequestMessage(HttpMethod.Post,
            "https://api.bochaai.com/v1/web-search");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _apiKey);
        request.Content = JsonContent.Create(payload, SearchJsonContext.Default.BochaRequest);

        using var response = await _http.SendAsync(request, ct);
        response.EnsureSuccessStatusCode();

        var body = await response.Content.ReadFromJsonAsync(SearchJsonContext.Default.BochaResponse, ct);
        var pages = body?.Data?.WebPages?.Value;

        if (pages is null || pages.Count == 0)
            return new List<SearchResult>();

        var results = new List<SearchResult>(pages.Count);
        for (int i = 0; i < pages.Count; i++)
        {
            var p = pages[i];
            if (string.IsNullOrEmpty(p.Url))
                continue;

            results.Add(new SearchResult
            {
                Query = query,
                Title = p.Name ?? string.Empty,
                Url = p.Url,
                Snippet = p.Summary ?? p.Description ?? string.Empty,
                // 位置衰减相关性: 引擎排序即权威, 第 i 名 = 1.0 * 0.9^i
                RelevanceScore = Math.Pow(0.9, i),
                Source = SearchResultSource.Provider,
                Keywords = new List<string> { "bocha" },
                Metadata = new Dictionary<string, object>
                {
                    ["provider"] = Name,
                    ["siteName"] = p.SiteName ?? string.Empty,
                    ["datePublished"] = p.DatePublished ?? string.Empty,
                },
            });
        }

        _logger.LogDebug("博查搜索 '{Query}' 返回 {Count} 条", query, results.Count);
        return results;
    }

    private static string MapFreshness(SearchOptions options)
    {
        if (options.FromDate.HasValue)
        {
            var from = options.FromDate.Value.ToString("yyyy-MM-dd");
            return options.ToDate.HasValue
                ? $"{from}..{options.ToDate.Value:yyyy-MM-dd}"
                : from;
        }
        return "noLimit";
    }
}

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

public class BochaResponse
{
    [JsonPropertyName("code")]
    public int Code { get; set; }

    [JsonPropertyName("log_id")]
    public string? LogId { get; set; }

    [JsonPropertyName("data")]
    public BochaData? Data { get; set; }
}

public class BochaData
{
    [JsonPropertyName("webPages")]
    public BochaWebPages? WebPages { get; set; }
}

public class BochaWebPages
{
    [JsonPropertyName("value")]
    public List<BochaPage>? Value { get; set; }
}

public class BochaPage
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("url")]
    public string? Url { get; set; }

    [JsonPropertyName("summary")]
    public string? Summary { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("siteName")]
    public string? SiteName { get; set; }

    [JsonPropertyName("datePublished")]
    public string? DatePublished { get; set; }
}
