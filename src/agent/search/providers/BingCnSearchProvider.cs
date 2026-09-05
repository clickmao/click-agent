using System.Text.RegularExpressions;
using Microsoft.Extensions.Logging;

namespace agent.search;

/// <summary>
/// Bing 中国 HTML 解析插件 (cn.bing.com/search, 免 Key 零配置兜底)。
/// 解析器基于显式 HTML 结构匹配 + 严格边界检查, 不引入 AngleSharp(减少依赖面)。
/// 反爬容忍: 429/挑战页抛异常交给编排层熔断, 绝不返回伪结果。
/// </summary>
public sealed partial class BingCnSearchProvider : ISearchProvider
{
    private readonly HttpClient _http;
    private readonly ILogger<BingCnSearchProvider> _logger;

    public string Name => "bingcn";
    public bool IsConfigured => true; // 免 Key
    public int DefaultPriority => 10; // 免 Key 且国内实测可达: 默认主槽 (2026-09 连通性实测 10/10 解析成功)

    public BingCnSearchProvider(HttpClient http, ILogger<BingCnSearchProvider> logger)
    {
        _http = http;
        _logger = logger;
    }

    public async Task<List<SearchResult>> SearchAsync(string query, SearchOptions options, CancellationToken ct)
    {
        var market = options.Language ?? "zh-CN";
        var url = $"https://cn.bing.com/search?q={Uri.EscapeDataString(query)}" +
                  $"&count={Math.Clamp(options.MaxResults, 1, 30)}&setmkt={Uri.EscapeDataString(market)}" +
                  "&setlang=" + Uri.EscapeDataString(market);

        using var request = new HttpRequestMessage(HttpMethod.Get, url);
        request.Headers.TryAddWithoutValidation("Accept-Language", $"{market},en;q=0.5");

        using var response = await _http.SendAsync(request, ct);
        response.EnsureSuccessStatusCode();

        var html = await response.Content.ReadAsStringAsync(ct);

        // 挑战/验证码页特征: 无结果列表容器
        if (!html.Contains("id=\"b_results\"", StringComparison.Ordinal))
        {
            _logger.LogWarning("Bing CN 返回非结果页 (可能是挑战页), query: {Query}", query);
            throw new InvalidOperationException("Bing CN 返回页无结果列表 (可能触发反爬)");
        }

        var results = ParseResults(html, query, options.MaxResults);
        _logger.LogDebug("Bing CN 搜索 '{Query}' 解析出 {Count} 条", query, results.Count);
        return results;
    }

    /// <summary>解析 b_algo 结果块: &lt;li class="b_algo"&gt;…&lt;h2&gt;&lt;a href=…&gt;标题&lt;/a&gt;…&lt;p&gt;摘要&lt;/p&gt;</summary>
    private List<SearchResult> ParseResults(string html, string query, int maxResults)
    {
        var results = new List<SearchResult>();
        var blocks = AlgoBlock().EnumerateMatches(html);

        int rank = 0;
        foreach (var match in blocks)
        {
            if (rank >= maxResults) break;

            var block = html.Substring(match.Index, match.Length);
            var link = HrefInBlock().Match(block);
            if (!link.Success || string.IsNullOrWhiteSpace(link.Groups[1].Value))
                continue;

            var title = StripTags(TitleInBlock().Match(block) is { Success: true } tm ? tm.Groups[1].Value : string.Empty);
            var snippet = StripTags(SnippetInBlock().Match(block) is { Success: true } sm ? sm.Groups[1].Value : string.Empty);

            if (string.IsNullOrEmpty(title))
                continue;

            rank++;
            results.Add(new SearchResult
            {
                Query = query,
                Title = title,
                Url = link.Groups[1].Value,
                Snippet = snippet,
                RelevanceScore = Math.Pow(0.85, rank - 1),
                Source = SearchResultSource.Provider,
                Keywords = new List<string> { "bingcn" },
                Metadata = new Dictionary<string, object> { ["provider"] = Name },
            });
        }

        return results;
    }

    private static string StripTags(string html)
    {
        var text = Tag().Replace(html, " ");
        text = Entity().Replace(text, m => m.Value switch
        {
            "&amp;" => "&",
            "&lt;" => "<",
            "&gt;" => ">",
            "&quot;" => "\"",
            "&#39;" or "&apos;" => "'",
            "&nbsp;" => " ",
            _ => m.Value,
        });
        return text.Trim();
    }

    // ── 源生成正则 (Compiled + AOT 兼容) ──

    [GeneratedRegex("<li class=\"b_algo\"[^>]*>(.*?)</li>", RegexOptions.Singleline)]
    private static partial Regex AlgoBlock();

    [GeneratedRegex("<h2[^>]*><a[^>]+href=\"(https?://[^\"]+)\"[^>]*>(.*?)</a>", RegexOptions.Singleline)]
    private static partial Regex HrefInBlock();

    [GeneratedRegex("<h2[^>]*>.*?<a[^>]*>(.*?)</a>", RegexOptions.Singleline)]
    private static partial Regex TitleInBlock();

    [GeneratedRegex("<p[^>]*>(.*?)</p>", RegexOptions.Singleline)]
    private static partial Regex SnippetInBlock();

    [GeneratedRegex("<[^>]+>")]
    private static partial Regex Tag();

    [GeneratedRegex("&(amp|lt|gt|quot|#39|apos|nbsp);")]
    private static partial Regex Entity();
}
