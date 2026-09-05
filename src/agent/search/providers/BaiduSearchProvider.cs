using System.Text.RegularExpressions;
using Microsoft.Extensions.Logging;

namespace agent.search;

/// <summary>
/// 百度 HTML 解析插件 (www.baidu.com/s, 免 Key, 中文搜索质量高)。
/// 结果块: &lt;div class="result c-container "&gt;…&lt;h3&gt;&lt;a href="http://www.baidu.com/link?url=…"&gt;标题&lt;/a&gt;…摘要容器。
/// 注意: 百度 href 是跳转链接 (/link?url=), 保留原样 —— 解析跳转需要额外请求, 成本过高;
/// 调用方(抓取层 WebReaper)跟随跳转即可。
/// </summary>
public sealed partial class BaiduSearchProvider : ISearchProvider
{
    private readonly HttpClient _http;
    private readonly ILogger<BaiduSearchProvider> _logger;

    public string Name => "baidu";
    public bool IsConfigured => true; // 免 Key
    public int DefaultPriority => 50; // 无 Key 兜底 (实测跳验证码页, 反爬形态运行时熔断处理)

    public BaiduSearchProvider(HttpClient http, ILogger<BaiduSearchProvider> logger)
    {
        _http = http;
        _logger = logger;
    }

    public async Task<List<SearchResult>> SearchAsync(string query, SearchOptions options, CancellationToken ct)
    {
        var url = $"https://www.baidu.com/s?wd={Uri.EscapeDataString(query)}" +
                  $"&rn={Math.Clamp(options.MaxResults, 1, 20)}" +
                  "&ie=utf-8";

        using var request = new HttpRequestMessage(HttpMethod.Get, url);
        request.Headers.TryAddWithoutValidation("Accept-Language", "zh-CN,zh;q=0.9");

        using var response = await _http.SendAsync(request, ct);
        response.EnsureSuccessStatusCode();

        var html = await response.Content.ReadAsStringAsync(ct);

        // 百度安全验证页特征
        if (html.Contains("百度安全验证", StringComparison.Ordinal) ||
            html.Contains("wappass.baidu.com", StringComparison.Ordinal))
        {
            _logger.LogWarning("百度返回安全验证页, query: {Query}", query);
            throw new InvalidOperationException("百度触发安全验证 (反爬)");
        }

        if (!html.Contains("class=\"result", StringComparison.Ordinal) &&
            !html.Contains("content_left", StringComparison.Ordinal))
        {
            throw new InvalidOperationException("百度返回页无结果结构");
        }

        var results = ParseResults(html, query, options.MaxResults);
        _logger.LogDebug("百度搜索 '{Query}' 解析出 {Count} 条", query, results.Count);
        return results;
    }

    private List<SearchResult> ParseResults(string html, string query, int maxResults)
    {
        var results = new List<SearchResult>();
        var blocks = ResultBlock().EnumerateMatches(html);

        int rank = 0;
        foreach (var match in blocks)
        {
            if (rank >= maxResults) break;

            var block = html.Substring(match.Index, match.Length);
            var link = Href().Match(block);
            if (!link.Success || string.IsNullOrWhiteSpace(link.Groups[1].Value))
                continue;

            var title = StripTags(Title().Match(block) is { Success: true } tm ? tm.Groups[1].Value : string.Empty);
            if (string.IsNullOrEmpty(title))
                continue;

            var snippet = StripTags(Snippet().Match(block) is { Success: true } sm ? sm.Groups[1].Value : string.Empty);

            rank++;
            results.Add(new SearchResult
            {
                Query = query,
                Title = title,
                Url = link.Groups[1].Value,
                Snippet = snippet,
                RelevanceScore = Math.Pow(0.82, rank - 1),
                Source = SearchResultSource.Provider,
                Keywords = new List<string> { "baidu" },
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

    [GeneratedRegex("<div[^>]+class=\"result[^\"]*c-container[^\"]*\"[^>]*>(.*?)(?=<div[^>]+class=\"result|<div id=\"page\")", RegexOptions.Singleline)]
    private static partial Regex ResultBlock();

    [GeneratedRegex("<h3[^>]*><a[^>]+href=\"([^\"]+)\"", RegexOptions.Singleline)]
    private static partial Regex Href();

    [GeneratedRegex("<h3[^>]*>\\s*<a[^>]*>(.*?)</a>", RegexOptions.Singleline)]
    private static partial Regex Title();

    [GeneratedRegex("class=\"c-abstract[^\"]*\"[^>]*>(.*?)</", RegexOptions.Singleline)]
    private static partial Regex Snippet();

    [GeneratedRegex("<[^>]+>")]
    private static partial Regex Tag();

    [GeneratedRegex("&(amp|lt|gt|quot|#39|apos|nbsp);")]
    private static partial Regex Entity();
}
