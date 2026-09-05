using System.Text.Json;
using Microsoft.Extensions.Logging;
using agent.userinteraction;

namespace agent.search;

/// <summary>
/// 搜索故障转移编排器 —— 插件化多源搜索的核心。
///
/// 槽位规则 (用户定义):
/// 1. 每个搜索源是一个插件, 分配到主槽(0)或备槽(1..n);
/// 2. 搜索按槽位顺序尝试: 主槽成功即返回; 主槽失败/熔断则依次降级到备槽;
/// 3. 主槽连续失败达到阈值即熔断, 第一个可用备槽自动提升为主槽(槽位交换);
/// 4. 槽位次序与健康统计持久化到磁盘, 下次启动复用 —— 被验证过不可靠的源
///    不会在每次重启后被重新授予主槽;
/// 5. 免费源 (DDG) 初始优先; 付费源 (博查等) 仅在配置了 Key 时参与;
///    Key 缺失时通过 IUserPromptService 向真实用户问询 (问询含作用说明 + 类型 flag),
///    用户提供后持久化到 credentials.json, 下次启动免问。
///
/// 参考: Polly 弹性策略 + Envoy outlier detection 的 ejection/promotion 模型。
/// </summary>
public sealed class SearchFailoverService : ISearchService
{
    private readonly ILogger<SearchFailoverService> _logger;
    private readonly SearchProvidersOptions _options;
    private readonly string _dataDir;
    private readonly IUserPromptService? _promptService;
    private readonly Lock _lock = new();

    /// <summary>已注册插件 (含未配置的)</summary>
    private readonly List<ISearchProvider> _providers;

    /// <summary>槽位 → 插件名 (index 0 = 主槽)</summary>
    private List<string> _slotOrder = new();

    /// <summary>插件健康状态</summary>
    private readonly Dictionary<string, ProviderHealth> _health =
        new(StringComparer.OrdinalIgnoreCase);

    /// <summary>结果缓存</summary>
    private readonly Dictionary<string, (SearchResult Result, DateTime CachedAt)> _cache = new();
    private readonly TimeSpan _cacheDuration = TimeSpan.FromHours(1);

    public SearchFailoverService(
        IEnumerable<ISearchProvider> providers,
        SearchProvidersOptions options,
        string dataStoragePath,
        ILogger<SearchFailoverService> logger,
        IUserPromptService? promptService = null)
    {
        _providers = providers.ToList();
        _options = options;
        _dataDir = string.IsNullOrWhiteSpace(dataStoragePath) ? "." : dataStoragePath;
        _logger = logger;
        _promptService = promptService;

        foreach (var p in _providers)
            _health[p.Name] = new ProviderHealth();

        LoadSlotState();
    }

    // ── ISearchService ──

    public async Task<SearchResult> SearchAsync(string query, SearchOptions? options = null, CancellationToken ct = default)
    {
        options ??= new SearchOptions();
        var cacheKey = query.Trim().ToLowerInvariant();

        if (TryGetCached(cacheKey, out var cached))
        {
            _logger.LogDebug("搜索缓存命中: {Query}", query);
            return cached;
        }

        // 首次使用时尝试补全未配置插件的凭据 (问真实用户)
        await EnsureProvidersConfiguredAsync(ct);

        var failures = new List<string>();
        foreach (var providerName in GetSlotOrderSnapshot())
        {
            var provider = ResolveProvider(providerName);
            if (provider is null || !provider.IsConfigured)
                continue;

            var health = _health[provider.Name];

            if (health.IsCircuitOpen)
            {
                _logger.LogDebug("插件 {Provider} 熔断中, 跳过", provider.Name);
                continue;
            }

            try
            {
                using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
                timeoutCts.CancelAfter(TimeSpan.FromSeconds(_options.ProviderTimeoutSeconds));

                var items = await provider.SearchAsync(query, options, timeoutCts.Token);

                health.RecordSuccess();
                PersistSlotStateSafe();

                var best = BuildAggregateResult(query, provider.Name, items);
                CacheResult(cacheKey, best);
                return best;
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested)
            {
                throw; // 外部取消, 不算插件失败
            }
            catch (Exception ex)
            {
                health.RecordFailure(_options.FailureThreshold);
                failures.Add($"{provider.Name}: {ex.Message}");

                if (health.IsCircuitOpen)
                {
                    _logger.LogWarning(
                        "插件 {Provider} 连续失败 {Count} 次, 熔断打开, 触发槽位重排",
                        provider.Name, health.ConsecutiveFailures);
                    PromoteNextAvailable(provider.Name);
                    PersistSlotStateSafe();
                }
            }
        }

        // 全部源失败 → 明确错误结果 (绝不伪造数据)
        _logger.LogError("全部搜索源失败: {Query}. 详情: {Failures}", query, string.Join("; ", failures));
        return new SearchResult
        {
            Query = query,
            Title = "Search Unavailable",
            Snippet = $"所有搜索源均不可用 ({failures.Count} 个源尝试失败)。详情: {string.Join("; ", failures)}",
            RelevanceScore = 0,
            Source = SearchResultSource.Provider,
            Metadata = new Dictionary<string, object>
            {
                ["error"] = true,
                ["failedProviders"] = failures.Count,
                ["attempts"] = string.Join(",", failures.Select(f => f.Split(':')[0])),
            },
        };
    }

    public async Task<IEnumerable<SearchResult>> BatchSearchAsync(
        IEnumerable<string> queries, BatchSearchOptions? options = null, CancellationToken ct = default)
    {
        options ??= new BatchSearchOptions();
        var queryList = queries.Where(q => !string.IsNullOrWhiteSpace(q)).Distinct().ToList();
        var results = new List<SearchResult>(queryList.Count);

        using var semaphore = new SemaphoreSlim(Math.Max(1, options.MaxConcurrency));
        var tasks = queryList.Select(async query =>
        {
            await semaphore.WaitAsync(ct);
            try
            {
                return await SearchAsync(query, options.DefaultOptions, ct);
            }
            finally
            {
                semaphore.Release();
            }
        });

        results.AddRange(await Task.WhenAll(tasks));
        return results;
    }

    public async Task<string> ExtractContentAsync(string url, ExtractOptions? options = null, CancellationToken ct = default)
    {
        options ??= new ExtractOptions();

        // 三级抓取策略 (2026-09: 库直引 AOT 探针验证 0 IL 警告 + 真实抓取成功):
        // ① WebReaper 库直引 (进程内, 无外部进程审批开销, AOT clean)
        // ② WebReaper CLI (进程隔离; ①不可用/异常时走此路, 敏感操作门禁审批)
        // ③ 内置 HTTP+HTML 提取 (最终兜底)
        try
        {
            var viaLib = await WebReaperContentExtractor.ExtractAsync(url, options, _logger, ct);
            if (!string.IsNullOrWhiteSpace(viaLib))
                return viaLib;
            // 库返回空 (无匹配 schema) → 继续尝试下一级
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "WebReaper 库内抓取异常, 降级下一级: {Url}", url);
        }

        var reaperPath = ResolveWebReaperPath();
        if (reaperPath is not null)
        {
            try
            {
                return await ExtractViaWebReaper(reaperPath, url, options, ct);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "WebReaper CLI 抓取失败, 降级为内置提取: {Url}", url);
            }
        }

        return await ExtractViaHttp(url, options, ct);
    }

    public Task<IEnumerable<SearchResult>> GetCachedResultsAsync(string query)
    {
        lock (_lock)
        {
            var key = query.Trim().ToLowerInvariant();
            if (_cache.TryGetValue(key, out var cached) &&
                DateTime.UtcNow - cached.CachedAt < _cacheDuration)
            {
                return Task.FromResult<IEnumerable<SearchResult>>(new[] { cached.Result });
            }
        }
        return Task.FromResult<IEnumerable<SearchResult>>(Array.Empty<SearchResult>());
    }

    public Task ClearCacheAsync()
    {
        lock (_lock)
        {
            _cache.Clear();
        }
        _logger.LogInformation("搜索缓存已清空");
        return Task.CompletedTask;
    }

    // ── WebReaper CLI 集成 (AOT 单二进制, 进程隔离) ──

    /// <summary>
    /// 定位 webreaper 可执行文件: 配置指定 → PATH → 常见安装位置。
    /// 找不到且用户配置了 CustomPath 时问询 (ExternalToolPath 类型, RealUserOnly)。
    /// </summary>
    private string? ResolveWebReaperPath()
    {
        if (!string.IsNullOrWhiteSpace(_options.WebReaperCliPath))
        {
            if (File.Exists(_options.WebReaperCliPath))
                return _options.WebReaperCliPath;
        }

        // PATH 探测 (linux/mac/windows)
        foreach (var name in OperatingSystem.IsWindows()
            ? new[] { "webreaper.exe", "webreaper.cmd" }
            : new[] { "webreaper" })
        {
            var pathVar = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
            foreach (var dir in pathVar.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
            {
                try
                {
                    var candidate = Path.Combine(dir.Trim(), name);
                    if (File.Exists(candidate))
                        return candidate;
                }
                catch { /* 非法 PATH 段忽略 */ }
            }
        }

        return null;
    }

    private async Task<string> ExtractViaWebReaper(
        string cliPath, string url, ExtractOptions options, CancellationToken ct)
    {
        // 敏感操作门禁: 执行外部程序前按托管级别审批 (Standard/Strict 问真实用户)
        if (_promptService is not null)
        {
            var approval = await _promptService.RequestOperationApprovalAsync(
                new SensitiveOperationRequest
                {
                    Kind = SensitiveOperationKind.ExecuteProcess,
                    Summary = $"执行外部抓取程序 webreaper 抓取页面",
                    Details = $"命令: {cliPath} scrape {url} --format md\n" +
                              "外部程序由 MIT 协议的 WebReaper (github.com/alex-on-ai/WebReaper) 提供, " +
                              "以独立进程运行, 无 shell 注入风险 (ArgumentList 传参)。",
                    Initiator = "SearchFailoverService",
                    Origin = new PromptOrigin
                    {
                        AskedByAgentId = "main",
                        AskingDepth = 0,
                        Authority = AnswerAuthority.MainAgentAllowed, // 只读抓取, 主 agent 可代答
                    },
                }, ct);

            if (!approval.Approved)
            {
                _logger.LogInformation("WebReaper 抓取被拒绝 ({By}), 降级为内置 HTTP 提取: {Url}",
                    approval.AnsweredBy, url);
                throw new InvalidOperationException("外部抓取未获批准");
            }
        }

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(TimeSpan.FromSeconds(Math.Max(5, options.TimeoutSeconds)));

        var psi = new System.Diagnostics.ProcessStartInfo
        {
            FileName = cliPath,
            ArgumentList =
            {
                "scrape", url,
                "--format", "md",
                "--max-length", options.MaxLength.ToString(),
            },
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        using var process = System.Diagnostics.Process.Start(psi)
            ?? throw new InvalidOperationException($"无法启动 webreaper: {cliPath}");

        var stdout = await process.StandardOutput.ReadToEndAsync(ct);
        var stderr = await process.StandardError.ReadToEndAsync(ct);

        await process.WaitForExitAsync(ct);
        if (process.ExitCode != 0)
            throw new InvalidOperationException($"webreaper 退出码 {process.ExitCode}: {Truncate(stderr, 300)}");

        var content = stdout.Trim();
        if (string.IsNullOrEmpty(content))
            throw new InvalidOperationException("webreaper 返回空内容");

        return content.Length > options.MaxLength ? content[..options.MaxLength] : content;
    }

    private async Task<string> ExtractViaHttp(string url, ExtractOptions options, CancellationToken ct)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, url);
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(TimeSpan.FromSeconds(Math.Max(1, options.TimeoutSeconds)));

        using var response = await SharedHttp.ForProviders().SendAsync(request, cts.Token);
        response.EnsureSuccessStatusCode();

        var html = await response.Content.ReadAsStringAsync(cts.Token);
        var text = CleanHtml(html);
        return text.Length > options.MaxLength ? text[..options.MaxLength] : text;
    }

    // ── 凭据问询集成 ──

    /// <summary>
    /// 扫描未配置的插件, 通过问询服务向真实用户请求凭据。
    /// 每个插件的问询带: 具体用途说明 + 不提供的降级路径 + CredentialRequestKind flag。
    /// 用户的回答持久化到 credentials.json, 会话内即时生效, 重启后不再问。
    /// </summary>
    private async Task EnsureProvidersConfiguredAsync(CancellationToken ct)
    {
        if (_promptService is null)
            return;

        foreach (var provider in _providers)
        {
            if (provider.IsConfigured)
                continue;

            // 已在本次会话中问过且被拒的不再重复问
            if (_credentialDeclined.Contains(provider.Name))
                continue;

            var request = BuildCredentialRequest(provider);
            if (request is null)
                continue;

            _logger.LogInformation("插件 {Provider} 缺少配置, 向用户问询", provider.Name);

            var answers = await _promptService.RequestCredentialsAsync(request, ct);
            if (answers is null)
            {
                _credentialDeclined.Add(provider.Name);
                _logger.LogInformation("用户未提供 {Provider} 凭据, 该源走降级路径", provider.Name);
                continue;
            }

            ApplyCredentials(provider.Name, answers);
        }
    }

    private readonly HashSet<string> _credentialDeclined = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>为插件构造具体化的问询请求 (用途说明必须让用户明白这 Key 用在哪)</summary>
    private static CredentialRequest? BuildCredentialRequest(ISearchProvider provider)
    {
        return provider switch
        {
            BochaSearchProvider => new CredentialRequest
            {
                Kind = CredentialRequestKind.ApiKey,
                ServiceName = "bocha",
                Purpose = "博查是国内专为 AI 场景的搜索 API (api.bochaai.com), 中文搜索准确度最高。" +
                          "提供 Key 后它将作为主搜索源之一参与故障转移; 每次搜索按次计费。",
                Items = new List<CredentialItem>
                {
                    new() { Key = "apiKey", DisplayName = "博查 API Key (open.bochaai.com 获取)", Sensitive = true },
                },
                FallbackNote = "将跳过博查, 继续使用免费的 DuckDuckGo 等源",
                Origin = PromptOrigin.Main(),
            },
            SearXngSearchProvider => new CredentialRequest
            {
                Kind = CredentialRequestKind.Endpoint,
                ServiceName = "searxng",
                Purpose = "SearXNG 是自建聚合搜索实例 (可聚合 Google/Bing 等数十引擎), " +
                          "提供实例地址后作为主搜索源之一; JSON API 输出, 结果质量可控。",
                Items = new List<CredentialItem>
                {
                    new() { Key = "endpoint", DisplayName = "SearXNG 实例地址 (如 http://localhost:8080)", Sensitive = false },
                },
                FallbackNote = "将跳过 SearXNG, 继续使用免费的 DuckDuckGo 等源",
                Origin = PromptOrigin.Main(),
            },
            _ => null, // 免费插件 (DDG/BingCN/百度) 无需问询
        };
    }

    /// <summary>把用户回答注入插件运行时 (热生效)</summary>
    private void ApplyCredentials(string providerName, Dictionary<string, string> answers)
    {
        if (providerName.Equals("bocha", StringComparison.OrdinalIgnoreCase) &&
            ResolveProvider("bocha") is BochaSearchProvider bocha &&
            answers.TryGetValue("apiKey", out var key))
        {
            bocha.SetApiKey(key);
            _logger.LogInformation("博查 API Key 已注入 (热生效)");
        }
        else if (providerName.Equals("searxng", StringComparison.OrdinalIgnoreCase) &&
            ResolveProvider("searxng") is SearXngSearchProvider searxng &&
            answers.TryGetValue("endpoint", out var endpoint))
        {
            searxng.SetEndpoint(endpoint);
            _logger.LogInformation("SearXNG 端点已注入 (热生效)");
        }
    }

    // ── 槽位管理 ──

    private List<string> GetSlotOrderSnapshot()
    {
        lock (_lock)
            return _slotOrder.ToList();
    }

    private ISearchProvider? ResolveProvider(string name)
    {
        foreach (var p in _providers)
            if (string.Equals(p.Name, name, StringComparison.OrdinalIgnoreCase))
                return p;
        return null;
    }

    /// <summary>
    /// 主槽失败熔断时: 第一个已配置且未熔断的备槽提升为主槽, 原主槽降级到队尾。
    /// </summary>
    private void PromoteNextAvailable(string failedProvider)
    {
        lock (_lock)
        {
            if (_slotOrder.Count == 0 ||
                !string.Equals(_slotOrder[0], failedProvider, StringComparison.OrdinalIgnoreCase))
                return;

            int promoteIndex = -1;
            for (int i = 1; i < _slotOrder.Count; i++)
            {
                var p = ResolveProvider(_slotOrder[i]);
                if (p is { IsConfigured: true } && !_health[p.Name].IsCircuitOpen)
                {
                    promoteIndex = i;
                    break;
                }
            }

            if (promoteIndex < 0)
            {
                _logger.LogWarning("无可用备槽可提升, 主槽 {Provider} 保留 (熔断冷却后重试)", failedProvider);
                return;
            }

            var promoted = _slotOrder[promoteIndex];
            _slotOrder.RemoveAt(promoteIndex);
            _slotOrder.RemoveAt(0);
            _slotOrder.Insert(0, promoted);
            _slotOrder.Add(failedProvider);

            _logger.LogInformation(
                "槽位变更: {Promoted} 提升为主槽, {Demoted} 降级到备槽. 当前次序: {Order}",
                promoted, failedProvider, string.Join(" → ", _slotOrder));
        }
    }

    // ── 槽位状态持久化 ──

    private void LoadSlotState()
    {
        try
        {
            var statePath = Path.Combine(_dataDir, _options.SlotStatePath ?? "search_slots.json");
            if (File.Exists(statePath))
            {
                var json = File.ReadAllText(statePath);
                var state = JsonSerializer.Deserialize(json, SearchJsonContext.Default.ProviderSlotState);

                if (state?.SlotOrder is { Count: > 0 })
                {
                    var known = _providers.Select(p => p.Name).ToHashSet(StringComparer.OrdinalIgnoreCase);
                    var valid = state.SlotOrder
                        .Where(known.Contains)
                        .Distinct(StringComparer.OrdinalIgnoreCase)
                        .ToList();

                    foreach (var p in _providers
                        .Where(p => !valid.Contains(p.Name, StringComparer.OrdinalIgnoreCase))
                        .OrderBy(p => p.DefaultPriority))
                        valid.Add(p.Name);

                    _slotOrder = valid;

                    foreach (var (name, snap) in state.Health)
                    {
                        if (_health.TryGetValue(name, out var h))
                        {
                            h.TotalSuccess = snap.TotalSuccess;
                            h.TotalFailures = snap.TotalFailures;
                            h.LastSuccessAt = snap.LastSuccessAt;
                            h.LastFailureAt = snap.LastFailureAt;
                        }
                    }

                    _logger.LogInformation(
                        "搜索槽位状态已恢复: {Order}", string.Join(" → ", _slotOrder));
                    return;
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "搜索槽位状态文件损坏, 使用默认槽位");
        }

        // 默认: 按 DefaultPriority (免费源优先)
        _slotOrder = _providers
            .Where(p => p.IsConfigured)
            .OrderBy(p => p.DefaultPriority)
            .Select(p => p.Name)
            .ToList();

        if (_slotOrder.Count == 0)
            _logger.LogWarning("没有任何已配置的搜索插件! 搜索将不可用");
        else
            _logger.LogInformation("搜索槽位初始化: {Order}", string.Join(" → ", _slotOrder));
    }

    private void PersistSlotStateSafe()
    {
        try
        {
            ProviderSlotState state;
            lock (_lock)
            {
                state = new ProviderSlotState
                {
                    SlotOrder = _slotOrder.ToList(),
                    SavedAtUtc = DateTime.UtcNow,
                    Health = _health.ToDictionary(
                        kv => kv.Key,
                        kv => ProviderHealthSnapshot.From(kv.Value),
                        StringComparer.OrdinalIgnoreCase),
                };
            }

            var statePath = Path.Combine(_dataDir, _options.SlotStatePath ?? "search_slots.json");
            var dir = Path.GetDirectoryName(statePath);
            if (!string.IsNullOrEmpty(dir))
                Directory.CreateDirectory(dir);

            File.WriteAllText(statePath, JsonSerializer.Serialize(state, SearchJsonContext.Default.ProviderSlotState));
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "搜索槽位状态持久化失败 (不影响搜索)");
        }
    }

    // ── 结果组装与缓存 ──

    private static SearchResult BuildAggregateResult(string query, string providerName, List<SearchResult> items)
    {
        if (items.Count == 0)
        {
            return new SearchResult
            {
                Query = query,
                Title = "No results",
                Snippet = $"[{providerName}] 未找到相关结果",
                RelevanceScore = 0,
                Source = SearchResultSource.Provider,
                Metadata = new Dictionary<string, object> { ["provider"] = providerName, ["empty"] = true },
            };
        }

        var top = items[0];
        return new SearchResult
        {
            Query = query,
            Title = top.Title,
            Url = top.Url,
            Snippet = top.Snippet,
            Content = string.Join("\n\n", items.Take(5).Select(i => $"[{i.Title}]({i.Url})\n{i.Snippet}")),
            RelevanceScore = items.Max(i => i.RelevanceScore),
            Source = SearchResultSource.Provider,
            Keywords = top.Keywords,
            Metadata = new Dictionary<string, object>
            {
                ["provider"] = providerName,
                ["totalResults"] = items.Count,
                ["urls"] = items.Take(5).Select(i => i.Url).ToList(),
            },
        };
    }

    private bool TryGetCached(string key, out SearchResult result)
    {
        lock (_lock)
        {
            if (_cache.TryGetValue(key, out var cached))
            {
                if (DateTime.UtcNow - cached.CachedAt < _cacheDuration)
                {
                    result = cached.Result;
                    return true;
                }
                _cache.Remove(key);
            }
        }
        result = null!;
        return false;
    }

    private void CacheResult(string key, SearchResult result)
    {
        lock (_lock)
        {
            if (_cache.Count >= 500)
            {
                var toRemove = _cache.OrderBy(kv => kv.Value.CachedAt).Take(250).Select(kv => kv.Key).ToList();
                foreach (var k in toRemove)
                    _cache.Remove(k);
            }
            _cache[key] = (result, DateTime.UtcNow);
        }
    }

    private static string Truncate(string s, int max) =>
        string.IsNullOrEmpty(s) || s.Length <= max ? s : s[..max] + "...";

    private static string CleanHtml(string html)
    {
        var text = HtmlScrubber.StripScriptStyle().Replace(html, string.Empty);
        text = HtmlScrubber.StripTags().Replace(text, " ");
        text = HtmlScrubber.CollapseWhitespace().Replace(text, " ");
        return text.Trim();
    }
}

/// <summary>
/// HTML 清洗的 source-gen 正则 (Native AOT: 编译期生成扫描器, 零运行时反射编译)。
/// </summary>
internal static partial class HtmlScrubber
{
    [System.Text.RegularExpressions.GeneratedRegex(
        "<(script|style)[^>]*>.*?</\\1>",
        System.Text.RegularExpressions.RegexOptions.Singleline |
        System.Text.RegularExpressions.RegexOptions.IgnoreCase)]
    internal static partial System.Text.RegularExpressions.Regex StripScriptStyle();

    [System.Text.RegularExpressions.GeneratedRegex("<[^>]+>")]
    internal static partial System.Text.RegularExpressions.Regex StripTags();

    [System.Text.RegularExpressions.GeneratedRegex("\\s+")]
    internal static partial System.Text.RegularExpressions.Regex CollapseWhitespace();
}
