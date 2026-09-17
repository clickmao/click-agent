using Microsoft.Extensions.Logging;
using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;
using agent.tokencompression;

namespace agent.context;

public partial class ContextAssembler : IContextAssembler
{
    
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

            // v0.11.0 R11: 工作区文件召回 — 之前只有配额定义无实现, 源恒空
            // R524: **缺省关** (用户 2026-09-17 定向「你往中间塞东西了？」+ 真机证据: 关键词召回把宿主自身运行产物
            //   (A0-off/side-run.json、logs-driver-*.txt、data/activity/<pid>.json) 当上下文塞进提示, 既烧 token
            //   又逐轮漂移; 需要时 AGENTFRAMEWORK_WORKSPACE_RECALL=on 显式开)。
            if (IsWorkspaceRecallEnabled() &&
                request.EnabledSources.Contains(DataSourceType.WorkspaceFiles) &&
                !string.IsNullOrEmpty(request.WorkspaceRoot) && Directory.Exists(request.WorkspaceRoot))
            {
                recallTasks.Add(RecallFromWorkspaceAsync(request, ct));
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
                        EstimatedTokens = EstimateTokens(request.SessionMemoryBlock), // v0.11.0 R48: R29 漏网 — 本源同样缺估算
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
                        EstimatedTokens = EstimateTokens(request.AgentContextBlock),
                    }
                }));
            }

            if (request.EnabledSources.Contains(DataSourceType.FixMemory) &&
                request.FixMemoryBlock != null)
            {
                // v0.14.0 T2d: 修法记忆 (输出侧经验 — 反模式→修法, 生成前少样本注入)
                recallTasks.Add(Task.FromResult(new List<ContextSnippet>
                {
                    new()
                    {
                        SourceType = DataSourceType.FixMemory,
                        SourceName = "fix_memory",
                        Content = request.FixMemoryBlock,
                        RelevanceScore = 0.92,
                        EstimatedTokens = EstimateTokens(request.FixMemoryBlock),
                    }
                }));
            }

            if (request.EnabledSources.Contains(DataSourceType.GuardrailMemory) &&
                request.GuardrailBlock != null)
            {
                // v0.15.2: 警告/铁律记忆 (用户主动警告的三元组 — 前置注入, 领域性联想抑制)
                recallTasks.Add(Task.FromResult(new List<ContextSnippet>
                {
                    new()
                    {
                        SourceType = DataSourceType.GuardrailMemory,
                        SourceName = "guardrail_memory",
                        Content = request.GuardrailBlock,
                        RelevanceScore = 0.95,
                        EstimatedTokens = EstimateTokens(request.GuardrailBlock),
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
                    _resultCache.TryRemove(k, out _);
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
    /// <summary>
    /// R524: 工作区文件自动召回开关 —— **缺省关**。真机证据: 该召回无索引、纯关键词匹配, 会把宿主自身运行产物
    /// (arm 的 side-run.json、驱动日志、data/activity/&lt;pid&gt;.json) 当"相关文件"塞进提示 ⇒ 白烧 token 且
    /// 逐轮漂移 (system 前缀被砍断在 4,477 字符处)。需要时 <c>AGENTFRAMEWORK_WORKSPACE_RECALL=on</c> 显式开。
    /// </summary>
    public static bool IsWorkspaceRecallEnabled()
    {
        var v = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_WORKSPACE_RECALL");
        if (string.IsNullOrWhiteSpace(v)) return false;
        return v.Trim().ToLowerInvariant() is "on" or "1" or "true" or "yes" or "enable" or "enabled";
    }

    /// <summary>
    /// R524: 自指遥测路径闸 —— 工作区召回**不得**把运行期状态当上下文召回。
    /// 判据 (结构, 与语言/后缀无关): ① 追加式日志 <c>*.jsonl</c>; ② 路径段 <c>/activity/</c> 或 <c>/telemetry/</c>
    /// (每进程一条、pid 命名、内容含题面原文); ③ 运行库 <c>state.db</c>。
    /// 依据: R522/R523 实发 system 比对 —— 该块把钩子文件召回进 system 后, 第 4,477 字符处即分叉 (缓存前沿被砍断)。
    /// 需要这些文件内容时, agent 仍可用自己的文件工具显式读取 (显式 ≠ 自动注入)。
    /// </summary>
    public static bool IsSelfTelemetryPath(string path)
    {
        if (string.IsNullOrEmpty(path)) return false;
        var p = path.Replace('\\', '/');
        if (p.EndsWith(".jsonl", StringComparison.OrdinalIgnoreCase)) return true;
        if (p.EndsWith("/state.db", StringComparison.OrdinalIgnoreCase)) return true;
        foreach (var seg in SelfTelemetrySegments)
            if (p.Contains(seg, StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }

    private static readonly string[] SelfTelemetrySegments = { "/activity/", "/telemetry/" };
    #endregion
}
