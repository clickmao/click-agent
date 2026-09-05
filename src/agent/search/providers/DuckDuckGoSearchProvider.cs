using System.Text.RegularExpressions;
using Microsoft.Extensions.Logging;

namespace agent.search;

/// <summary>
/// DuckDuckGo HTML 解析插件 (html.duckduckgo.com/html/, 免 Key)。
/// 用户明确要求: 免费源优先, 付费 API 仅在免费源失败/用户主动配置时启用。
/// 解析 target: &lt;a class="result__a" href="..."&gt;标题&lt;/a&gt; + &lt;a class="result__snippet"&gt;摘要&lt;/a&gt;
/// DDG 的 href 可能是跳转 "//duckduckgo.com/l/?uddg=<encoded>", 需解码还原真实 URL。
/// </summary>
public sealed partial class DuckDuckGoSearchProvider : ISearchProvider
{
    private readonly HttpClient _http;
    private readonly ILogger<DuckDuckGoSearchProvider> _logger;

    public string Name => "duckduckgo";
    public bool IsConfigured => true; // 免 Key
    public int DefaultPriority => 40; // 免 Key 备槽 (国内网络实测超时, 首查熔断代价 ~10s)

    public DuckDuckGoSearchProvider(HttpClient http, ILogger<DuckDuckGoSearchProvider> logger)
    {
        _http = http;
        _logger = logger;
    }

    public async Task<List<SearchResult>> SearchAsync(string query, SearchOptions options, CancellationToken ct)
    {
        // POST 表单比 GET 更不易被拦截 (html.duckduckgo.com 的标准用法)
        using var request = new HttpRequestMessage(HttpMethod.Post,
            "https://html.duckduckgo.com/html/");
        request.Content = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["q"] = query,
            ["kl"] = options.Language ?? "cn-zh",
        });

        using var response = await _http.SendAsync(request, ct);
        response.EnsureSuccessStatusCode();

        var html = await response.Content.ReadAsStringAsync(ct);

        // 异常页特征: DDG 被限流时返回 anomaly 页面
        if (html.Contains("anomaly", StringComparison.OrdinalIgnoreCase) &&
            !html.Contains("result__a", StringComparison.Ordinal))
        {
            _logger.LogWarning("DDG 返回异常检测页 (限流/反爬), query: {Query}", query);
            throw new InvalidOperationException("DDG 触发异常检测 (限流)");
        }

        var results = ParseResults(html, query, options.MaxResults);
        _logger.LogDebug("DDG 搜索 '{Query}' 解析出 {Count} 条", query, results.Count);
        return results;
    }

    private List<SearchResult> ParseResults(string html, string query, int maxResults)
    {
        var results = new List<SearchResult>();

        // 逐块: result__a 链接 + 其后最近的 result__snippet
        var links = ResultLink().EnumerateMatches(html);
        var snippets = Snippet().Matches(html);

        int rank = 0;
        int snippetIdx = 0;
        foreach (var match in links)
        {
            if (rank >= maxResults) break;

            var block = html.Substring(match.Index, match.Length);
            var href = Href().Match(block).Groups[1].Value;
            var title = StripTags(Title().Match(block).Groups[1].Value);

            if (string.IsNullOrWhiteSpace(href) || string.IsNullOrEmpty(title))
                continue;

            var realUrl = DecodeRedirect(href);
            if (string.IsNullOrEmpty(realUrl))
                continue;

            string snippet = string.Empty;
            if (snippetIdx < snippets.Count)
                snippet = StripTags(snippets[snippetIdx].Groups[1].Value);
            snippetIdx++;

            rank++;
            results.Add(new SearchResult
            {
                Query = query,
                Title = title,
                Url = realUrl,
                Snippet = snippet,
                RelevanceScore = Math.Pow(0.88, rank - 1),
                Source = SearchResultSource.Provider,
                Keywords = new List<string> { "duckduckgo" },
                Metadata = new Dictionary<string, object> { ["provider"] = Name },
            });
        }

        return results;
    }

    /// <summary>还原 DDG 跳转链接: //duckduckgo.com/l/?uddg=&lt;urlencoded&gt;&amp;rut=... → 真实 URL</summary>
    private static string DecodeRedirect(string href)
    {
        if (href.Contains("/l/?uddg=", StringComparison.OrdinalIgnoreCase))
        {
            var idx = href.IndexOf("uddg=", StringComparison.OrdinalIgnoreCase);
            if (idx >= 0)
            {
                var encoded = href[(idx + 5)..];
                var amp = encoded.IndexOf('&');
                if (amp >= 0)
                    encoded = encoded[..amp];
                try
                {
                    return Uri.UnescapeDataString(encoded);
                }
                catch
                {
                    return string.Empty;
                }
            }
            return string.Empty;
        }

        if (href.StartsWith("//", StringComparison.Ordinal))
            return "https:" + href;
        if (href.StartsWith("http", StringComparison.OrdinalIgnoreCase))
            return href;
        return string.Empty; // 内部链接/广告位, 丢弃
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
            "&#x27;" or "&#39;" or "&apos;" => "'",
            "&nbsp;" => " ",
            _ => m.Value,
        });
        return text.Trim();
    }

    // ── 源生成正则 (Compiled + AOT 兼容) ──

    [GeneratedRegex("<a[^>]+class=\"[^\"]*result__a[^\"]*\"[^>]*>(.*?)</a>", RegexOptions.Singleline)]
    private static partial Regex ResultLink();

    [GeneratedRegex("href=\"([^\"]+)\"", RegexOptions.Singleline)]
    private static partial Regex Href();

    [GeneratedRegex(">(.*?)<", RegexOptions.Singleline)]
    private static partial Regex Title();

    [GeneratedRegex("<a[^>]+class=\"[^\"]*result__snippet[^\"]*\"[^>]*>(.*?)</a>", RegexOptions.Singleline)]
    private static partial Regex Snippet();

    [GeneratedRegex("<[^>]+>")]
    private static partial Regex Tag();

    [GeneratedRegex("&(amp|lt|gt|quot|#x27|#39|apos|nbsp);")]
    private static partial Regex Entity();
}
