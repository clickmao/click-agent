using Microsoft.Extensions.Logging;
using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;
using agent.tokencompression;

namespace agent.context;

/// <summary>
/// 上下文组装器实现
/// 
/// 参考了以下工业级框架的最佳实践：
/// - Microsoft Semantic Kernel: Context 变量和组装机制
/// - LangChain: Retrieval 和 Composable Memory
/// - Anthropic Claude Code: Context 压缩和优先级机制
/// </summary>
public class ContextAssembler : IContextAssembler
{
    private readonly ILogger<ContextAssembler> _logger;
    private readonly IRAGRecall _ragRecall;
    private readonly ISessionManager _sessionManager;
    private readonly ITendencyAnalyzer _tendencyAnalyzer;
    private readonly ISearchService _searchService;
    private readonly ITokenCompressor _tokenCompressor;
    
    // 缓存：snippetId -> ContextSnippet
    private readonly Dictionary<string, ContextSnippet> _snippetCache = new();
    private readonly Dictionary<string, List<string>> _sessionSnippetCache = new();
    
    // 统计
    private long _totalAssemblies;
    private long _totalSnippets;
    private long _totalTokensAssembled;
    private long _totalRecallTimeMs;
    private readonly System.Collections.Concurrent.ConcurrentDictionary<DataSourceType, long> _recallCountBySource = new();

    private sealed record CachedResult(ContextAssemblyResult Result, DateTime CachedAt);
    private readonly Dictionary<string, CachedResult> _resultCache = new();
    private static readonly TimeSpan CacheTtl = TimeSpan.FromMinutes(5);

    private static string ComputeCacheKey(ContextAssemblyRequest request)
    {
        var sources = string.Join(",", request.EnabledSources.OrderBy(s => s.ToString()));
        return $"{request.UserMessage.GetHashCode():X}|{request.SessionId}|{sources}";
    }

    private long _cacheHits;
    private long _cacheMisses;
    
    private readonly object _lock = new();
    
    public ContextAssembler(
        ILogger<ContextAssembler> logger,
        IRAGRecall ragRecall,
        ISessionManager sessionManager,
        ITendencyAnalyzer tendencyAnalyzer,
        ISearchService searchService,
        ITokenCompressor tokenCompressor,
        agent.contextgradient.ITextEmbedder? embedder = null)
    {
        _logger = logger;
        _ragRecall = ragRecall;
        _sessionManager = sessionManager;
        _tendencyAnalyzer = tendencyAnalyzer;
        _searchService = searchService;
        _tokenCompressor = tokenCompressor;
        _gradientCompressor = new agent.contextgradient.ContextGradientCompressor(embedder);

        // 初始化统计计数器
        foreach (DataSourceType source in Enum.GetValues<DataSourceType>())
        {
            _recallCountBySource[source] = 0;
        }
    }
    
    /// <summary>
    /// 主入口：组装多数据源上下文
    /// </summary>
    public async Task<ContextAssemblyResult> AssembleAsync(
        ContextAssemblyRequest request, 
        CancellationToken ct = default)
    {
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        var result = new ContextAssemblyResult();
        
        try
        {
            // 0. 缓存检查: 同签名请求 (用户消息+源集合) 直接命中 (5min TTL)
var cacheKey = ComputeCacheKey(request);
if (_resultCache.TryGetValue(cacheKey, out var cached) && DateTime.UtcNow - cached.CachedAt < CacheTtl)
{
    Interlocked.Increment(ref _cacheHits);
    cached.Result.FromCache = true;
    return cached.Result;
}
Interlocked.Increment(ref _cacheMisses);

        _logger.LogInformation("Starting context assembly for message: {Preview}", 
                request.UserMessage.Length > 50 ? request.UserMessage[..50] + "..." : request.UserMessage);
            
            // 1. 并行召回所有数据源
            var recallTasks = new List<Task<List<ContextSnippet>>>();
            
            if (request.EnabledSources.Contains(DataSourceType.Memory))
            {
                recallTasks.Add(RecallFromMemoryAsync(request, ct));
            }
            
            if (request.EnabledSources.Contains(DataSourceType.Session))
            {
                recallTasks.Add(RecallFromSessionAsync(request, ct));
            }
            
            if (request.EnabledSources.Contains(DataSourceType.WebSearch))
            {
                recallTasks.Add(RecallFromWebAsync(request, ct));
            }
            
            if (request.EnabledSources.Contains(DataSourceType.UserTendency))
            {
                recallTasks.Add(RecallFromUserTendencyAsync(request, ct));
            }

            if (request.EnabledSources.Contains(DataSourceType.SessionMemory) &&
                request.SessionMemoryBlock != null)
            {
                // 会话长期记忆 + 目标画像 (v7.14): 宿主预渲染好的记忆块 (SessionMemory.RenderForPrompt)
                recallTasks.Add(Task.FromResult(new List<ContextSnippet>
                {
                    new()
                    {
                        SourceType = DataSourceType.SessionMemory,
                        SourceName = "session_memory",
                        Content = request.SessionMemoryBlock,
                        RelevanceScore = 0.95, // 方向指示优先级最高
                    }
                }));
            }

            if (request.EnabledSources.Contains(DataSourceType.AgentContext) &&
                request.AgentContextBlock != null)
            {
                // Agent 画像 + 能力清单 (v7.14): 宿主预渲染 (AgentProfile.RenderForPrompt + CapabilityScanner.RenderForPrompt)
                recallTasks.Add(Task.FromResult(new List<ContextSnippet>
                {
                    new()
                    {
                        SourceType = DataSourceType.AgentContext,
                        SourceName = "agent_context",
                        Content = request.AgentContextBlock,
                        RelevanceScore = 0.9,
                    }
                }));
            }
            
            // 等待所有召回完成
            var recallResults = await Task.WhenAll(recallTasks);
            var allSnippets = recallResults.SelectMany(x => x).ToList();
            
            _logger.LogInformation("Retrieved {Count} snippets from {Sources} sources",
                allSnippets.Count, recallResults.Length);
            
            // 2. 过滤低相关性片段
            allSnippets = allSnippets
                .Where(s => s.RelevanceScore >= request.MinRelevanceScore)
                .ToList();
            
            // 3. 估算 Token 并分配配额
            var tokenAllocation = CalculateTokenAllocation(allSnippets, request);
            
            // 4. 压缩超限的片段
            if (request.EnableCompression)
            {
                allSnippets = await CompressSnippetsAsync(allSnippets, tokenAllocation, request, ct);
            }
            
            // 5. 按相关性排序并截取
            allSnippets = allSnippets
                .OrderByDescending(s => s.RelevanceScore)
                .ThenByDescending(s => s.CreatedAt)
                .TakeWhile((_, index) => index < 20) // 最多20个片段
                .ToList();
            
            // 7. 先组装 Prompt Header（确定实际进入 Prompt 的内容）
            result.PromptHeader = BuildPromptHeader(allSnippets, request);
            result.Snippets = allSnippets;
            
            // 6. 实际 Token 数 = 真正进入 Prompt 的 header token（而非全量片段 token，
            //    BuildPromptHeader 会按源分组/每源限量/截断，直接 Sum 会高估预算占用）
            var actualTokens = EstimateTokens(result.PromptHeader);
            result.TotalTokens = actualTokens;
            result.TokenBudgetUsage = request.MaxTokenBudget > 0
                ? (double)actualTokens / request.MaxTokenBudget
                : 0;
            
            // 8. 生成统计
            foreach (DataSourceType source in Enum.GetValues<DataSourceType>())
            {
                var sourceSnippets = allSnippets.Where(s => s.SourceType == source).ToList();
                result.SourceStats[source] = new DataSourceStats
                {
                    SourceType = source,
                    SnippetCount = sourceSnippets.Count,
                    TotalTokens = sourceSnippets.Sum(s => s.EstimatedTokens),
                    AvgRelevanceScore = sourceSnippets.Any() 
                        ? sourceSnippets.Average(s => s.RelevanceScore) : 0
                };
            }
            
            // 更新全局统计
            Interlocked.Increment(ref _totalAssemblies);
            Interlocked.Add(ref _totalSnippets, allSnippets.Count);
            Interlocked.Add(ref _totalTokensAssembled, actualTokens);
            Interlocked.Add(ref _totalRecallTimeMs, stopwatch.ElapsedMilliseconds);
            
            result.AssemblyTimeMs = stopwatch.ElapsedMilliseconds;
            result.Success = true;
            
            _logger.LogInformation(
                "Context assembly completed: {Snippets} snippets, {Tokens} tokens, {TimeMs}ms",
                allSnippets.Count, actualTokens, stopwatch.ElapsedMilliseconds);

            // 成功结果写入缓存 (过期懒清理)
            _resultCache[cacheKey] = new CachedResult(result, DateTime.UtcNow);
            if (_resultCache.Count > 128)
            {
                var expiredKeys = _resultCache
                    .Where(kv => DateTime.UtcNow - kv.Value.CachedAt >= CacheTtl)
                    .Select(kv => kv.Key).ToList();
                foreach (var k in expiredKeys)
                    _resultCache.Remove(k);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error assembling context");
            result.Success = false;
            result.Error = ex.Message;
            result.Warnings.Add($"组装失败: {ex.Message}");
        }
        
        return result;
    }
    
    /// <summary>
    /// 带进度的异步组装
    /// </summary>
    public async IAsyncEnumerable<ContextSnippet> AssembleWithProgressAsync(
        ContextAssemblyRequest request,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken ct = default)
    {
        // 并行召回并逐个 yield
        var tasks = new List<(DataSourceType source, Task<List<ContextSnippet>> task)>();
        
        if (request.EnabledSources.Contains(DataSourceType.Memory))
        {
            tasks.Add((DataSourceType.Memory, RecallFromMemoryAsync(request, ct)));
        }
        
        if (request.EnabledSources.Contains(DataSourceType.Session))
        {
            tasks.Add((DataSourceType.Session, RecallFromSessionAsync(request, ct)));
        }
        
        if (request.EnabledSources.Contains(DataSourceType.WebSearch))
        {
            tasks.Add((DataSourceType.WebSearch, RecallFromWebAsync(request, ct)));
        }
        
        if (request.EnabledSources.Contains(DataSourceType.UserTendency))
        {
            tasks.Add((DataSourceType.UserTendency, RecallFromUserTendencyAsync(request, ct)));
        }
        
        // 并行执行，逐个返回结果
        while (tasks.Any())
        {
            var completedTask = await Task.WhenAny(tasks.Select(t => t.task).ToArray());
            var source = tasks.First(t => t.task == completedTask).source;
            
            var snippets = await completedTask;
            _recallCountBySource.AddOrUpdate(source, 1, (_, v) => v + 1);
            
            foreach (var snippet in snippets)
            {
                if (snippet.RelevanceScore >= request.MinRelevanceScore)
                {
                    yield return snippet;
                }
            }
            
            tasks.RemoveAll(t => t.task == completedTask);
        }
    }
    
    /// <summary>
    /// 快速获取摘要
    /// </summary>
    public async Task<ContextSummary> GetQuickSummaryAsync(
        string userMessage,
        string sessionId,
        int maxSnippets = 5)
    {
        var summary = new ContextSummary();
        
        try
        {
            // 快速召回
            var request = new ContextAssemblyRequest
            {
                UserMessage = userMessage,
                SessionId = sessionId,
                MaxTokenBudget = 500,
                EnabledSources = new HashSet<DataSourceType> { DataSourceType.Memory, DataSourceType.Session }
            };
            
            var snippets = await Task.WhenAll(
                RecallFromMemoryAsync(request, CancellationToken.None),
                RecallFromSessionAsync(request, CancellationToken.None)
            );
            
            var allSnippets = snippets.SelectMany(x => x)
                .OrderByDescending(s => s.RelevanceScore)
                .Take(maxSnippets)
                .ToList();
            
            summary.TotalSnippets = allSnippets.Count;
            summary.EstimatedTokens = allSnippets.Sum(s => s.EstimatedTokens);
            
            foreach (var snippet in allSnippets)
            {
                if (!summary.SnippetsBySource.ContainsKey(snippet.SourceType))
                {
                    summary.SnippetsBySource[snippet.SourceType] = 0;
                }
                summary.SnippetsBySource[snippet.SourceType]++;
                
                // 提取关键词作为主题
                var words = snippet.Content.Split(' ', StringSplitOptions.RemoveEmptyEntries)
                    .Take(3);
                summary.KeyTopics.AddRange(words);
            }
            
            summary.KeyTopics = summary.KeyTopics.Distinct().Take(10).ToList();
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Error getting quick summary");
        }
        
        return summary;
    }
    
    /// <summary>
    /// 失效缓存
    /// </summary>
    public Task InvalidateAsync(string snippetId)
    {
        lock (_lock)
        {
            _snippetCache.Remove(snippetId);
            
            // 从会话缓存中移除
            foreach (var list in _sessionSnippetCache.Values)
            {
                list.Remove(snippetId);
            }
        }
        
        _logger.LogDebug("Invalidated snippet cache: {SnippetId}", snippetId);
        return Task.CompletedTask;
    }
    
    /// <summary>
    /// 获取统计
    /// </summary>
    public ContextAssemblerStats GetStats()
    {
        lock (_lock)
        {
            return new ContextAssemblerStats
            {
                TotalAssemblies = _totalAssemblies,
                TotalSnippets = _totalSnippets,
                TotalTokensAssembled = _totalTokensAssembled,
                AvgAssemblyTimeMs = _totalAssemblies > 0 
                    ? (double)_totalRecallTimeMs / _totalAssemblies : 0,
                RecallCountBySource = new Dictionary<DataSourceType, long>(_recallCountBySource),
                CacheHits = _cacheHits,
                CacheMisses = _cacheMisses
            };
        }
    }
    
    #region Private Methods
    
    /// <summary>
    /// 从 Memory 召回
    /// </summary>
    private async Task<List<ContextSnippet>> RecallFromMemoryAsync(
        ContextAssemblyRequest request,
        CancellationToken ct)
    {
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        var snippets = new List<ContextSnippet>();
        
        try
        {
            var ragRequest = new rag.RecallRequest
            {
                Query = request.UserMessage,
                SessionId = request.SessionId,
                UserId = request.UserId,
                TopK = 10,
                MinScore = request.MinRelevanceScore
            };
            
            var results = await _ragRecall.RecallAsync(ragRequest);
            
            foreach (var result in results)
            {
                var snippet = new ContextSnippet
                {
                    Id = result.Document.Id,
                    SourceType = DataSourceType.Memory,
                    SourceName = "RAG Memory",
                    Content = result.HighlightedContent ?? result.Document.Content,
                    RelevanceScore = result.Score,
                    CreatedAt = result.Document.CreatedAt,
                    Metadata = result.Document.Metadata,
                    Tags = result.Document.Keywords,
                    EstimatedTokens = EstimateTokens(result.Document.Content)
                };
                
                snippets.Add(snippet);
                
                // 缓存
                lock (_lock)
                {
                    _snippetCache[snippet.Id] = snippet;
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Error recalling from memory");
        }
        
        _recallCountBySource.AddOrUpdate(DataSourceType.Memory, stopwatch.ElapsedMilliseconds, (_, v) => v + stopwatch.ElapsedMilliseconds);
        
        return snippets;
    }
    
    /// <summary>
    /// 从 Session 召回
    /// </summary>
    private async Task<List<ContextSnippet>> RecallFromSessionAsync(
        ContextAssemblyRequest request,
        CancellationToken ct)
    {
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        var snippets = new List<ContextSnippet>();
        
        try
        {
            if (string.IsNullOrEmpty(request.SessionId))
            {
                return snippets;
            }
            
            var session = await _sessionManager.GetSessionAsync(request.SessionId);
            if (session == null)
            {
                return snippets;
            }
            
            // 获取相关历史消息（基于关键词匹配; keywords 一次提取供过滤与打分共用, v7.8 消 M 次重复提取）
            var userMessageKeywords = ExtractKeywords(request.UserMessage);
            
            var matched = new List<Message>();
            foreach (var m in session.Messages)
            {
                if (m.Role == MessageRole.System)
                    continue;
                foreach (var k in userMessageKeywords)
                {
                    if (m.Content.Contains(k, StringComparison.OrdinalIgnoreCase))
                    {
                        matched.Add(m);
                        break;
                    }
                }
            }
            
            // 命中子集排序截取 (v7.8: 排序不作用于全表)
            matched.Sort(static (a, b) => b.Timestamp.CompareTo(a.Timestamp));
            var relevantMessages = matched.Count > 10 
                ? matched.GetRange(0, 10) 
                : matched;
            
            // 如果没有关键词匹配，取最近的消息
            if (relevantMessages.Count == 0)
            {
                // 兜底: 取最近 5 条 (倒序遍历尾部, 免全表排序)
                var recent = new List<Message>(5);
                for (var i = session.Messages.Count - 1; i >= 0 && recent.Count < 5; i--)
                {
                    if (session.Messages[i].Role != MessageRole.System)
                        recent.Add(session.Messages[i]);
                }
                relevantMessages = recent;
            }
            
            for (int i = 0; i < relevantMessages.Count; i++)
            {
                var msg = relevantMessages[i];
                var relevanceScore = CalculateMessageRelevance(msg, request.UserMessage, userMessageKeywords);
                
                var snippet = new ContextSnippet
                {
                    Id = $"session_{session.Id}_{msg.Id}",
                    SourceType = DataSourceType.Session,
                    SourceName = $"Session {session.Id}",
                    Content = $"[{msg.Role}] {msg.Content}",
                    RelevanceScore = relevanceScore,
                    CreatedAt = msg.Timestamp,
                    Metadata = new Dictionary<string, object>
                    {
                        { "messageId", msg.Id },
                        { "role", msg.Role.ToString() },
                        { "index", i }
                    },
                    EstimatedTokens = EstimateTokens(msg.Content),
                    Tags = new List<string> { msg.Role.ToString().ToLower() }
                };
                
                snippets.Add(snippet);
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Error recalling from session");
        }
        
        _recallCountBySource.AddOrUpdate(DataSourceType.Session, stopwatch.ElapsedMilliseconds, (_, v) => v + stopwatch.ElapsedMilliseconds);
        
        return snippets;
    }
    
    /// <summary>
    /// 从网络搜索召回
    /// </summary>
    private async Task<List<ContextSnippet>> RecallFromWebAsync(
        ContextAssemblyRequest request,
        CancellationToken ct)
    {
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        var snippets = new List<ContextSnippet>();
        
        try
        {
            // 检查是否需要网络搜索
            if (!ShouldSearchWeb(request.UserMessage))
            {
                return snippets;
            }
            
            var searchResult = await _searchService.SearchAsync(
                request.UserMessage, 
                new SearchOptions { MaxResults = 3 }, 
                ct);
            
            if (searchResult != null && !string.IsNullOrEmpty(searchResult.Snippet))
            {
                var snippet = new ContextSnippet
                {
                    Id = $"web_{Guid.NewGuid():N}",
                    SourceType = DataSourceType.WebSearch,
                    SourceName = "Web Search",
                    Content = $"[Search: {searchResult.Title}]\n{searchResult.Snippet}\nSource: {searchResult.Url}",
                    RelevanceScore = 0.8,
                    CreatedAt = DateTime.UtcNow,
                    Metadata = new Dictionary<string, object>
                    {
                        { "url", searchResult.Url ?? "" },
                        { "title", searchResult.Title ?? "" }
                    },
                    EstimatedTokens = EstimateTokens(searchResult.Snippet),
                    Tags = new List<string> { "search", "web" }
                };
                
                snippets.Add(snippet);
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Error searching web");
        }
        
        _recallCountBySource.AddOrUpdate(DataSourceType.WebSearch, stopwatch.ElapsedMilliseconds, (_, v) => v + stopwatch.ElapsedMilliseconds);
        
        return snippets;
    }
    
    /// <summary>
    /// 从用户倾向召回
    /// </summary>
    private async Task<List<ContextSnippet>> RecallFromUserTendencyAsync(
        ContextAssemblyRequest request,
        CancellationToken ct)
    {
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        var snippets = new List<ContextSnippet>();
        
        try
        {
            if (string.IsNullOrEmpty(request.UserId))
            {
                return snippets;
            }
            
            var bias = await _tendencyAnalyzer.GetContextBiasAsync(request.UserId, request.UserMessage);
            
            if (bias != null && bias.OverallConfidence > 0.3)
            {
                var content = new System.Text.StringBuilder();
                content.AppendLine("### User Preferences");
                
                if (bias.BiasScores.Any())
                {
                    content.AppendLine("**Detected Preferences:**");
                    foreach (var kvp in bias.BiasScores.OrderByDescending(x => x.Value).Take(5))
                    {
                        content.AppendLine($"- {kvp.Key}: {kvp.Value:P0}");
                    }
                }
                
                var snippet = new ContextSnippet
                {
                    Id = $"tendency_{request.UserId}",
                    SourceType = DataSourceType.UserTendency,
                    SourceName = "User Tendency",
                    Content = content.ToString(),
                    RelevanceScore = bias.OverallConfidence,
                    CreatedAt = DateTime.UtcNow,
                    Metadata = new Dictionary<string, object>
                    {
                        { "confidence", bias.OverallConfidence }
                    },
                    EstimatedTokens = EstimateTokens(content.ToString()),
                    Tags = new List<string> { "preference", "tendency" }
                };
                
                snippets.Add(snippet);
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Error recalling from tendency");
        }
        
        _recallCountBySource.AddOrUpdate(DataSourceType.UserTendency, stopwatch.ElapsedMilliseconds, (_, v) => v + stopwatch.ElapsedMilliseconds);
        
        return snippets;
    }
    
    /// <summary>
    /// 计算 Token 分配
    /// </summary>
    private Dictionary<DataSourceType, int> CalculateTokenAllocation(
        List<ContextSnippet> snippets,
        ContextAssemblyRequest request)
    {
        var allocation = new Dictionary<DataSourceType, int>();
        var totalQuota = request.SourceTokenQuota.Values.Sum();
        
        foreach (var source in request.EnabledSources)
        {
            var quota = request.SourceTokenQuota.GetValueOrDefault(source, 500);
            allocation[source] = Math.Min(quota, request.MaxTokenBudget);
        }
        
        return allocation;
    }
    
    /// <summary>
    /// 压缩片段
    /// </summary>
    private agent.contextgradient.ContextGradientCompressor _gradientCompressor;

    static ContextAssembler()
    {
    }

    /// <summary>P3: bge 嵌入器注入 (可选) — 语义漂移校验启用; null → 纯锚词模式</summary>
    public agent.contextgradient.ITextEmbedder? Embedder
    {
        set => _gradientCompressor = new agent.contextgradient.ContextGradientCompressor(value);
    }

    /// <summary>锚词提取 (P1 启发式: 取出现 ≥2 次的 2-8 字中英词段, 前 8 个; P3 向量版替换)</summary>
    private static List<string> ExtractAnchorWords(string content)
    {
        var words = new Dictionary<string, int>(StringComparer.Ordinal);
        // 英文词
        foreach (System.Text.RegularExpressions.Match m in
                 System.Text.RegularExpressions.Regex.Matches(content, "[A-Za-z]{3,}"))
        {
            var w = m.Value.ToLowerInvariant();
            words[w] = words.GetValueOrDefault(w) + 1;
        }
        // 中文 2-4 字词 (滑动窗, 出现 ≥2 次)
        for (var len = 2; len <= 4; len++)
        {
            for (var i = 0; i + len <= content.Length; i++)
            {
                if (!char.IsLetter(content[i]) || content[i] < 0x4E00 || content[i] > 0x9FFF)
                    continue;
                var w = content.Substring(i, len);
                words[w] = words.GetValueOrDefault(w) + 1;
            }
        }
        return words.Where(kv => kv.Value >= 2)
            .OrderByDescending(kv => kv.Value)
            .Take(8)
            .Select(kv => kv.Key)
            .ToList();
    }

    private async Task<List<ContextSnippet>> CompressSnippetsAsync(
        List<ContextSnippet> snippets,
        Dictionary<DataSourceType, int> allocation,
        ContextAssemblyRequest request,
        CancellationToken ct)
    {
        var compressed = new List<ContextSnippet>();
        
        // v7.14: 会话记忆/Agent 上下文是"目标锚"块 — RenderForPrompt 已自控体积 (记忆≤1000 字符),
        // 压缩会破坏 [目标]/[约束] 结构与画像统计, 且它们相关性最高 (0.95/0.9), 压缩收益为负
        var pinnedSources = new HashSet<DataSourceType>
        {
            DataSourceType.SessionMemory,
            DataSourceType.AgentContext,
        };

        foreach (var snippet in snippets)
        {
            var quota = allocation.GetValueOrDefault(snippet.SourceType, 500);

            if (!pinnedSources.Contains(snippet.SourceType) &&
                snippet.EstimatedTokens > quota / 10) // 超过配额的 1/10 才压缩
            {
                // v7.15: 梯度压缩优先 (相关性分层 L0-L3 + 锚词防漂移内置回退)
                // 锚词 = 片段内容中提取的实词 (简单启发: 高频中英词), P3 换向量匹配
                var anchors = ExtractAnchorWords(snippet.Content);
                var gradient = await _gradientCompressor.CompressAsync(new agent.contextgradient.GradientRequest
                {
                    Content = snippet.Content,
                    RelevanceScore = snippet.RelevanceScore,
                    TokenBudget = quota / Math.Max(1, snippets.Count(s => s.SourceType == snippet.SourceType)),
                    AnchorWords = anchors,
                });
                var compressedContent = gradient.DriftCheckPassed || gradient.Level == agent.contextgradient.GradientLevel.Full
                    ? gradient.Content
                    : snippet.Content; // 漂移校验失败且非全文 → 保原文 (宁大不歪)

                snippet.CompressedContent = compressedContent;
                snippet.IsCompressed = compressedContent != snippet.Content;
                snippet.EstimatedTokens = await _tokenCompressor.CountTokensAsync(compressedContent);
            }
            
            compressed.Add(snippet);
        }
        
        return compressed;
    }
    
    /// <summary>
    /// 构建 Prompt Header（优化版，减少格式开销）
    /// </summary>
    private string BuildPromptHeader(
        List<ContextSnippet> snippets,
        ContextAssemblyRequest request)
    {
        if (!snippets.Any())
            return string.Empty;
        
        var sb = new System.Text.StringBuilder();
        
        // 注意: 不加 "=== CONTEXT ===" 包装 —— 由 Prompt.Compose() 统一负责,
        // 避免双重包装污染最终 Prompt
        
        // 按数据源分组
        // v7.14: pinned 源 (会话记忆/Agent 上下文) 恒入选, 其余按相关性补足 — 方向锚不因预算被挤掉
        var pinnedTypes = new HashSet<DataSourceType>
        {
            DataSourceType.SessionMemory,
            DataSourceType.AgentContext,
        };
        var grouped = snippets.GroupBy(s => s.SourceType)
            .OrderByDescending(g => pinnedTypes.Contains(g.Key) ? 2.0 : g.Max(s => s.RelevanceScore))
            .Take(5) // 最多5个数据源 (3→5: pinned 占 2 席后其余源仍有 3 席)
            .ToList();
        
        for (int i = 0; i < grouped.Count; i++)
        {
            var group = grouped[i];
            var sourceName = GetSourceDisplayName(group.Key);
            var snippets_list = group.Take(2).ToList(); // 每个源最多2条
            
            // 数据源标题（简洁格式）
            sb.AppendLine($"[{sourceName}]");
            
            foreach (var snippet in snippets_list)
            {
                var content = snippet.IsCompressed && !string.IsNullOrEmpty(snippet.CompressedContent)
                    ? snippet.CompressedContent
                    : snippet.Content;
                
                // v7.14: pinned 源 (记忆/画像) 内容自控体积, 整块保留;
                // 其余基于 Token 截断
                var truncated = pinnedTypes.Contains(group.Key)
                    ? content
                    : TruncateByTokens(content, 200); // 每条最多200 tokens
                sb.AppendLine(truncated);
            }
            
            if (i < grouped.Count - 1)
                sb.AppendLine();
        }
        
        return sb.ToString();
    }
    
    /// <summary>
    /// 估算 Token 数（改进版，支持中文）
    /// </summary>
    private int EstimateTokens(string text)
    {
        if (string.IsNullOrEmpty(text)) return 0;
        
        double tokens = 0;
        var i = 0;
        
        while (i < text.Length)
        {
            var c = text[i];
            
            // 中文字符范围 (CJK Unified Ideographs)
            if (c >= 0x4E00 && c <= 0x9FFF)
            {
                tokens += 1;
                i++;
            }
            // 日文/韩文
            else if ((c >= 0x3040 && c <= 0x309F) || // Hiragana
                     (c >= 0x30A0 && c <= 0x30FF) || // Katakana
                     (c >= 0xAC00 && c <= 0xD7AF))    // Korean
            {
                tokens += 1;
                i++;
            }
            // 空白字符直接跳过 (必须在 ASCII 分支前判断, 否则死循环)
            else if (char.IsWhiteSpace(c))
            {
                i++;
            }
            // ASCII 字母/数字/标点
            else if (c < 128)
            {
                tokens += 0.25;
                // 统计连续的非空白字符 (整词计 1 个 token)
                while (i < text.Length && text[i] < 128 && !char.IsWhiteSpace(text[i]))
                {
                    i++;
                }
            }
            // 标点符号
            else if (IsPunctuation(c))
            {
                tokens += 0.25;
                i++;
            }
            // 其他Unicode字符
            else
            {
                tokens += 1;
                i++;
            }
        }
        
        return (int)Math.Ceiling(tokens);
    }
    
    /// <summary>
    /// 判断是否为标点符号
    /// </summary>
    private bool IsPunctuation(char c)
    {
        return c == '.' || c == ',' || c == ';' || c == ':' || 
               c == '!' || c == '?' || c == '"' || c == '\'' ||
               c == '(' || c == ')' || c == '[' || c == ']' ||
               c == '{' || c == '}' || c == '-' || c == '_' ||
               c == '+' || c == '=' || c == '/' || c == '\\' ||
               c == '|' || c == '@' || c == '#' || c == '$' ||
               c == '%' || c == '^' || c == '&' || c == '*' ||
               c == '<' || c == '>' || c == '`' || c == '~' ||
               c == '「' || c == '」' || c == '『' || c == '』' || // 中文引号
               c == '【' || c == '】' ||
               c == '—' || c == '…' || c == '·'; // 特殊符号
    }
    
    /// <summary>
    /// 截断内容（基于 Token 而非字符数）
    /// </summary>
    private string TruncateByTokens(string text, int maxTokens)
    {
        if (string.IsNullOrEmpty(text)) return text;
        
        double tokens = 0;
        var i = 0;
        var result = new System.Text.StringBuilder();
        
        while (i < text.Length && tokens < maxTokens)
        {
            var c = text[i];
            
            // 中文字符
            if (c >= 0x4E00 && c <= 0x9FFF)
            {
                result.Append(c);
                tokens += 1;
                i++;
            }
            // 日文/韩文
            else if ((c >= 0x3040 && c <= 0x309F) || (c >= 0x30A0 && c <= 0x30FF) || (c >= 0xAC00 && c <= 0xD7AF))
            {
                result.Append(c);
                tokens += 1;
                i++;
            }
            // ASCII
            else if (c < 128)
            {
                result.Append(c);
                tokens += 0.25;
                i++;
            }
            // 其他
            else
            {
                result.Append(c);
                tokens += 1;
                i++;
            }
        }
        
        if (i < text.Length)
        {
            result.Append("... [截断]");
        }
        
        return result.ToString();
    }
    
    /// <summary>
    /// 提取关键词
    /// </summary>
    /// <summary>停用词表 (v7.8: static readonly, 消每次调用分配)</summary>
    private static readonly HashSet<string> StopWords = new(StringComparer.OrdinalIgnoreCase)
    {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being"
    };
    
    private static List<string> ExtractKeywords(string text)
    {
        return text
            .Split(' ', StringSplitOptions.RemoveEmptyEntries)
            .Where(w => w.Length > 2 && !StopWords.Contains(w))
            .Take(10)
            .ToList();
    }
    
    /// <summary>
    /// 计算消息相关性
    /// </summary>
    private double CalculateMessageRelevance(Message message, string query, List<string>? precomputedKeywords = null)
    {
        var keywords = precomputedKeywords ?? ExtractKeywords(query);
        var matches = 0;
        foreach (var k in keywords)
        {
            if (message.Content.Contains(k, StringComparison.OrdinalIgnoreCase))
                matches++;
        }
        
        return matches > 0 ? (double)matches / keywords.Count : 0.1;
    }
    
    /// <summary>
    /// 判断是否需要网络搜索
    /// </summary>
    private bool ShouldSearchWeb(string message)
    {
        var searchIndicators = new[] 
        { 
            "最新", "今天", "当前", "now", "latest", "recent",
            "搜索", "search", "查找", "find",
            "什么是", "what is", "how to", "怎么", "如何"
        };
        
        return searchIndicators.Any(i => 
            message.Contains(i, StringComparison.OrdinalIgnoreCase));
    }
    
    /// <summary>
    /// 获取数据源显示名称
    /// </summary>
    private string GetSourceDisplayName(DataSourceType sourceType)
    {
        return sourceType switch
        {
            DataSourceType.Memory => "Memory (RAG)",
            DataSourceType.Session => "Session History",
            DataSourceType.WebSearch => "Web Search",
            DataSourceType.UserTendency => "User Preference",
            DataSourceType.WorkspaceFiles => "Workspace Files",
            DataSourceType.ToolOutput => "Tool Output",
            _ => sourceType.ToString()
        };
    }
    
    #endregion
}
