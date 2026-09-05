using System.Net.Http.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.search;

/// <summary>
/// SearXNG 搜索插件 (自建聚合实例, JSON API: /search?q=...&format=json)
/// 聚合 Google/Bing/DDG 等数十个引擎, 准确度高且实例自主可控。
/// 官方仓库: github.com/searxng/searxng (36k★)
/// </summary>
public sealed class SearXngSearchProvider : ISearchProvider
{
    private readonly HttpClient _http;
    private readonly ILogger<SearXngSearchProvider> _logger;
    private string _endpoint;

    public string Name => "searxng";
    public bool IsConfigured => !string.IsNullOrWhiteSpace(_endpoint);
    public int DefaultPriority => 30;

    public SearXngSearchProvider(HttpClient http, ILogger<SearXngSearchProvider> logger, string? endpoint = null)
    {
        _http = http;
        _logger = logger;
        _endpoint = string.IsNullOrWhiteSpace(endpoint) ? string.Empty : endpoint.TrimEnd('/');
    }

    /// <summary>端点问询后热注入</summary>
    public void SetEndpoint(string endpoint)
    {
        if (!string.IsNullOrWhiteSpace(endpoint))
            _endpoint = endpoint.TrimEnd('/');
    }

    public async Task<List<SearchResult>> SearchAsync(string query, SearchOptions options, CancellationToken ct)
    {
        if (!IsConfigured)
            throw new InvalidOperationException("SearXNG 实例地址未配置 (Search:Providers:searxng:endpoint)");

        var url = $"{_endpoint}/search?q={Uri.EscapeDataString(query)}&format=json" +
                  $"&language={Uri.EscapeDataString(options.Language ?? "zh-CN")}";

        using var response = await _http.GetAsync(url, ct);
        response.EnsureSuccessStatusCode();

        var body = await response.Content.ReadFromJsonAsync(SearchJsonContext.Default.SearXngResponse, ct);
        var entries = body?.Results;

        if (entries is null || entries.Count == 0)
            return new List<SearchResult>();

        var maxScore = entries.Max(r => (double?)r.Score) ?? 1.0;
        if (maxScore <= 0) maxScore = 1.0;

        var results = new List<SearchResult>(entries.Count);
        foreach (var r in entries
            .OrderByDescending(r => r.Score)
            .Take(options.MaxResults))
        {
            if (string.IsNullOrEmpty(r.Url))
                continue;

            results.Add(new SearchResult
            {
                Query = query,
                Title = r.Title ?? string.Empty,
                Url = r.Url,
                Snippet = r.Content ?? string.Empty,
                // 归一化聚合分: score/maxScore ∈ (0,1]
                RelevanceScore = Math.Max(0.05, r.Score / maxScore),
                Source = SearchResultSource.Provider,
                Keywords = new List<string> { "searxng" },
                Metadata = new Dictionary<string, object>
                {
                    ["provider"] = Name,
                    ["engines"] = string.Join(",", r.Engines ?? new List<string>()),
                },
            });
        }

        _logger.LogDebug("SearXNG 搜索 '{Query}' 返回 {Count} 条", query, results.Count);
        return results;
    }
}

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

public class SearXngResult
{
    [JsonPropertyName("url")]
    public string? Url { get; set; }

    [JsonPropertyName("title")]
    public string? Title { get; set; }

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    [JsonPropertyName("score")]
    public double Score { get; set; }

    [JsonPropertyName("engine")]
    public string? Engine { get; set; }

    [JsonPropertyName("engines")]
    public List<string>? Engines { get; set; }
}
