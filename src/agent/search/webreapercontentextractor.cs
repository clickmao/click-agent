using Microsoft.Extensions.Logging;
using WebReaper.Builders;

namespace agent.search;

/// <summary>
/// WebReaper 库内内容提取器 (net10.0 NuGet 直引, 进程内运行)。
/// 相比 CLI 方案: 无外部进程开销、无执行审批门禁 (非外部程序)、异常栈完整。
/// AOT: 上游 CLI 同链路 (ADR-0043 AOT 警告=error), 本工程探针实测 0 IL 警告 + ELF 发布成功。
/// </summary>
public static class WebReaperContentExtractor
{
    /// <summary>
    /// 抓取单页并按 title/text 提取正文。返回 JSON 字符串 (ParsedData.Data);
    /// 无内容/失败抛异常由调用方降级。超时默认 20s。
    /// </summary>
    public static async Task<string> ExtractAsync(
        string url, ExtractOptions options, ILogger logger, CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(url) || !Uri.TryCreate(url, UriKind.Absolute, out var uri))
            throw new InvalidOperationException($"非法 URL: {url}");

        var timeout = TimeSpan.FromSeconds(options.TimeoutSeconds > 0 ? options.TimeoutSeconds : 20);
        using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeoutCts.CancelAfter(timeout);

        var collected = new List<string>();
        var engine = await ScraperEngineBuilder
            .Crawl(url)
            .Extract(new()
            {
                new("title", "title"),
                new("text", "p")
            })
            .Subscribe(data => collected.Add(data.Data?.ToString() ?? string.Empty))
            .PageCrawlLimit(1)
            .WithParallelismDegree(1)
            .BuildAsync();

        await engine.RunAsync(timeoutCts.Token);

        var best = collected.FirstOrDefault(s => !string.IsNullOrWhiteSpace(s));
        if (string.IsNullOrWhiteSpace(best))
            throw new InvalidOperationException($"WebReaper 库内抓取无内容: {url}");

        logger.LogDebug("WebReaper 库内提取成功: {Url} ({Length} chars)", url, best.Length);
        return best;
    }
}
