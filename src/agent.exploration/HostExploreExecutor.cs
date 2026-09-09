using System.Text.RegularExpressions;
namespace agent.exploration;

/// <summary>
/// v0.13.3 R286 — 探索执行器宿主实现 (IExploreExecutor): 思考链的"手"。
/// URL → HttpClient 只读 GET (10s 超时, 抓 title/正文前 2KB digest);
/// Directory/File → 工作区内只读列举/读头 (路径穿越防护);
/// Text/ContextBlock → digest 直返 (无需 IO)。
/// </summary>
public sealed partial class HostExploreExecutor : IExploreExecutor
{
    [GeneratedRegex(@"<title[^>]*>(.*?)</title>", RegexOptions.Singleline | RegexOptions.IgnoreCase)]
    private static partial Regex TitlePattern();

    [GeneratedRegex(@"https?://[^\s,，。;；)""']+")]
    private static partial Regex UrlPattern();

    private static readonly HttpClient Http = new(new SocketsHttpHandler
    {
        // 探索只读 + 快速失败: 不跟随过多跳转, 不留连接池负担
        AllowAutoRedirect = true,
        MaxAutomaticRedirections = 3,
        ConnectTimeout = TimeSpan.FromSeconds(10),
    })
    {
        Timeout = TimeSpan.FromSeconds(15),
    };

    private readonly string _workspaceRoot;

    public HostExploreExecutor(string workspaceRoot) => _workspaceRoot = Path.GetFullPath(workspaceRoot);

    public async Task<ExploreStepResult> ExecuteAsync(ExploreNode node, CancellationToken ct = default)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var result = new ExploreStepResult
        {
            Kind = node.Kind,
            Ref = node.Ref,
            StepN = 0,
        };
        try
        {
            switch (node.Kind)
            {
                case ExploreSourceKind.Url:
                    await FetchUrl(node, result, ct);
                    break;
                case ExploreSourceKind.Directory:
                    ListDirectory(node, result);
                    break;
                case ExploreSourceKind.File:
                    await ReadFile(node, result, ct);
                    break;
                case ExploreSourceKind.Text:
                case ExploreSourceKind.ContextBlock:
                default:
                    result.Ok = true;
                    result.Digest = node.Ref.Length > 500 ? node.Ref[..500] : node.Ref;
                    break;
            }
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            result.Ok = false;
            result.Error = ex.Message.Length > 120 ? ex.Message[..120] : ex.Message;
        }
        sw.Stop();
        result.Ms = (int)sw.ElapsedMilliseconds;
        return result;
    }

    private async Task FetchUrl(ExploreNode node, ExploreStepResult result, CancellationToken ct)
    {
        using var resp = await Http.GetAsync(node.Ref, HttpCompletionOption.ResponseHeadersRead, ct);
        if (!resp.IsSuccessStatusCode)
        {
            result.Ok = false;
            result.Error = $"HTTP {(int)resp.StatusCode}";
            return;
        }
        var mediaType = resp.Content.Headers.ContentType?.MediaType ?? "";
        if (!mediaType.StartsWith("text/", StringComparison.Ordinal) && !mediaType.Contains("json") && !mediaType.Contains("xml"))
        {
            result.Ok = false;
            result.Error = $"非文本类型: {mediaType}";
            return;
        }
        var body = await resp.Content.ReadAsStringAsync(ct);
        result.Ok = true;
        result.Bytes = body.Length;
        // Digest: title + 正文去标签前 2KB
        var title = TitlePattern().Match(body);
        var text = title.Success ? title.Groups[1].Value + "。 " : "";
        text += Regex.Replace(body, @"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ");
        text = Regex.Replace(text, @"\s+", " ").Trim();
        result.Digest = text.Length > 2048 ? text[..2048] : text;
        // 页面内 URL 发现 (渐进探索: 上下文外链接 → 队列, 受 per-source 预算约束)
        foreach (Match m in UrlPattern().Matches(text))
        {
            var u = m.Value;
            if (u.Length > 8 && !u.Equals(node.Ref, StringComparison.OrdinalIgnoreCase))
                result.Discovered.Add(new ExploreNode
                {
                    Kind = ExploreSourceKind.Url,
                    Ref = u,
                    DiscoveredFrom = node.Ref,
                    FromContext = false,
                    Priority = node.Priority - 1, // 深层链接降优先级
                });
            if (result.Discovered.Count >= 5) break; // 每页发现上限
        }
    }

    private void ListDirectory(ExploreNode node, ExploreStepResult result)
    {
        var full = Path.GetFullPath(Path.Combine(_workspaceRoot, node.Ref));
        if (!full.StartsWith(_workspaceRoot, StringComparison.Ordinal))
        {
            result.Ok = false;
            result.Error = "路径越界 (workspace root 之外)";
            return;
        }
        if (!Directory.Exists(full))
        {
            result.Ok = false;
            result.Error = "目录不存在";
            return;
        }
        var entries = Directory.EnumerateFileSystemEntries(full).Take(30).ToList();
        result.Ok = true;
        result.Digest = "目录条目: " + string.Join(", ", entries.Select(Path.GetFileName));
        foreach (var e in entries.Take(5))
        {
            var rel = Path.GetRelativePath(_workspaceRoot, e);
            result.Discovered.Add(new ExploreNode
            {
                Kind = Directory.Exists(e) ? ExploreSourceKind.Directory : ExploreSourceKind.File,
                Ref = rel,
                DiscoveredFrom = node.Ref,
                FromContext = false,
                Priority = node.Priority - 1,
            });
        }
    }

    private async Task ReadFile(ExploreNode node, ExploreStepResult result, CancellationToken ct)
    {
        var full = Path.GetFullPath(Path.Combine(_workspaceRoot, node.Ref));
        if (!full.StartsWith(_workspaceRoot, StringComparison.Ordinal))
        {
            result.Ok = false;
            result.Error = "路径越界 (workspace root 之外)";
            return;
        }
        if (!File.Exists(full))
        {
            result.Ok = false;
            result.Error = "文件不存在";
            return;
        }
        var head = new char[2048];
        await using var fs = File.OpenRead(full);
        using var reader = new StreamReader(fs);
        var n = await reader.ReadAsync(head, ct);
        result.Ok = true;
        result.Bytes = new FileInfo(full).Length;
        result.Digest = new string(head, 0, n);
    }
}
