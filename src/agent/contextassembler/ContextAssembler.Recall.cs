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

    /// v0.11.0 R11: 工作区文件召回 — 轻量关键词匹配 (无索引), 查询词命中文件行 → 携上下文成片段。
    /// 上限 3 文件 / 每文件 1 片段, 防淹没 prompt。
    /// </summary>
    private async Task<List<ContextSnippet>> RecallFromWorkspaceAsync(
        ContextAssemblyRequest request, CancellationToken ct)
    {
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        var snippets = new List<ContextSnippet>();
        try
        {
            var keywords = ExtractQueryKeywords(request.UserMessage);
            if (keywords.Count == 0)
                return snippets;

            // R462 (承 R447 语言无关令): 原**硬编码后缀白名单** (源码逐字列语言后缀) 已移除 ——
            // 判定改为结构+内容探针 (agent.context.WorkspaceTextProbe): 空文件/NUL/二进制 ⇒ 弃,
            // 后缀集只在显式配置 (AGENTFRAMEWORK_TEXT_SUFFIX_ALLOWLIST) 时生效 ⇒ 换语言复用零噪声。
            var files = Directory.EnumerateFiles(request.WorkspaceRoot!, "*.*", SearchOption.AllDirectories)
                .Where(f => !f.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}") &&
                            !f.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}") &&
                            !f.Contains($"{Path.DirectorySeparatorChar}node_modules{Path.DirectorySeparatorChar}"))
                // R524: 自指遥测闸 —— 运行期状态文件 (活动文件/审计 jsonl/telemetry) 不是"相关上下文",
                // 却是按运行变化的字节 (含 pid 与题面原文) ⇒ 一旦被召回注入即砍断 provider 命中前沿。
                .Where(f => !IsSelfTelemetryPath(f))
                // v0.11.0 R30: 大仓库防慢上限保留, 但按修改时间降序 — 最近工作优先,
                // 避免目录序恰好漏掉最新文件 (数据边界: 扫描上限内的召回质量)
                .OrderByDescending(f => { try { return File.GetLastWriteTimeUtc(f); } catch { return DateTime.MinValue; } })
                .Take(300)
                .ToList();

            // P4 (R330): 整轮累计已读字节 (流式扫描近似) — 超 WorkspaceRecallBytesBudget 即停
            long totalBytesRead = 0;

            foreach (var file in files)
            {
                if (snippets.Count >= 3)
                    break;
                ct.ThrowIfCancellationRequested();
                try
                {
                    var info = new FileInfo(file);
                    if (info.Length > WorkspaceMaxFileBytes)
                        continue;
                    if (info.Length <= 0)
                        continue; // P4 (R330): 空文件跳过, 免开流
                    // R462: 结构+内容探针 (空/NUL/二进制 ⇒ 弃; 后缀集仅在显式配置时生效)。
                    if (!agent.context.WorkspaceTextProbe.IsUsableTextFile(file))
                        continue;
                    // P4 (R330): 整轮字节预算 — 若读该文件将超预算则停止扫描剩余 (文件按修改时间
                    // 降序, 丢的是最旧文件; 与 Take(300) 同哲学: 扫描窗口内的召回质量)。
                    if (totalBytesRead + info.Length > WorkspaceRecallBytesBudget)
                        break;
                    // P4 (R330): 原 ReadAllTextAsync 整读 + Split 全行数组 (数千短 string 分配/文件,
                    // ≤200KB/文件 × ≤300 文件 → 单轮最多 ~60MB 文本读入) → StreamReader 逐行流式:
                    // 峰值内存 = 单行; 满分档 (5 hits) 命中即停, 免读文件剩余。
                    var (hitLine, hitCount, bytesScanned) =
                        await FindKeywordLineRankedStreamingAsync(file, keywords, ct);
                    totalBytesRead += bytesScanned;
                    if (hitLine == null)
                        continue;

                    var excerpt = hitLine.Length > 400 ? hitLine[..400] + "…" : hitLine;
                    var workspaceContent = $"[工作区文件 {Path.GetRelativePath(request.WorkspaceRoot!, file)}]\n{excerpt}";
                    // R462 召回-现实一致性闸 (只打假, 一致时零字节注入 ⇒ 不增 token):
                    //   片段里若引用**别处**的文件事实而当前工作区没有 ⇒ 显式标 ✗, 使「召回陈旧引用」可见。
                    workspaceContent = agent.core.RecallRealityGate.Verify(workspaceContent, request.WorkspaceRoot, failOnly: true);
                    // v0.11.0 R118 (真缺陷 50): 相关分原硬编码 0.7 — 1 词命中与多词命中同分,
                    // 打点 r0.7rel 恒定失真, 无法支撑后续预算/排序。改按命中关键词数比例化。
                    var relevance = 0.4 + 0.5 * Math.Min(1.0, hitCount / 5.0);
                    snippets.Add(new ContextSnippet
                    {
                        Id = file,
                        SourceType = DataSourceType.WorkspaceFiles,
                        SourceName = Path.GetFileName(file),
                        Content = workspaceContent,
                        RelevanceScore = Math.Round(relevance, 2),
                        EstimatedTokens = EstimateTokens(workspaceContent), // v0.11.0 R29: 补 token 估算 (0tok 显示瑕疵真因)
                        CreatedAt = info.LastWriteTimeUtc,
                    });


                }
                catch (IOException) { /* 文件被占用等 — 跳过 */ }
                catch (UnauthorizedAccessException) { /* 无权限 — 跳过 */ }

            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Workspace recall failed");
        }

        // R129 D3: per-source 耗时可见化 (workspace 目录扫描+全文读取嫌疑)
        agent.config.AgentTelemetry.Emit("phase_timing", "ContextAssembler",
            ("phase", "recall_workspace"), ("ms", stopwatch.ElapsedMilliseconds));
        return snippets;
    }

    private static List<string> ExtractQueryKeywords(string text)
    {
        // 复用 2-gram 中文 + 英文词的轻量提取
        var words = text.Split(new[] { ' ', '\t', '\n', '\r', '.', ',', '!', '?', ';', ':', '，', '。', '？', '：', '；', '的', '了', '吗', '呢', '吧', '啊' },
            StringSplitOptions.RemoveEmptyEntries);
        var kws = new List<string>();
        foreach (var w in words)
        {
            var t = w.Trim();
            if (t.Length >= 2 && t.Length <= 30)
                kws.Add(t);
            for (var i = 0; i + 2 <= t.Length; i++)
            {
                if (t[i] >= 0x4e00 && t[i] <= 0x9fff && t[i + 1] >= 0x4e00 && t[i + 1] <= 0x9fff)
                    kws.Add(t.Substring(i, 2));
            }
        }
        return kws.Distinct().ToList();
    }

    private static string? FindKeywordLine(string content, List<string> keywords)
    {
        foreach (var line in content.Split('\n'))
        {
            foreach (var kw in keywords)
            {
                if (line.Contains(kw, StringComparison.OrdinalIgnoreCase))
                    return line.Trim();
            }
        }
        return null;
    }

    /// <summary>R118: 找最佳命中行并统计该行命中的关键词数 (缺陷 50 — 相关分按真实命中质量)。
    /// 字符串内存版 — 保留供 WorkspaceRelevanceTests 反射锚定 + 小内容场景。
    /// P4 (R330): 行命中计数抽到 CountKeywordHitsInLine, 与流式版共享同一语义。</summary>
    private static (string? Line, int Hits) FindKeywordLineRanked(string content, List<string> keywords)
    {
        string? best = null;
        var bestHits = 0;
        foreach (var line in content.Split('\n'))
        {
            var hits = CountKeywordHitsInLine(line, keywords);
            if (hits > bestHits)
            {
                bestHits = hits;
                best = line.Trim();
                if (bestHits >= 5) break; // 满分档提前退出
            }
        }
        return (best, bestHits);
    }

    /// <summary>P4 (R330): 流式逐行版 — 工作区召回用。峰值内存 = 单行 (原 ReadAllText + Split 全行数组)。
    /// 语义与字符串版完全一致: 全文件范围最佳命中行 (无前缀截断, 尾部命中不丢); 满分档 (5 hits) 提前停读。
    /// bytes 为已读行字符近似 (UTF-8 中文 3 字节/字符 — 预算为粗粒度防慢, 不追求精确)。</summary>
    private static async Task<(string? Line, int Hits, long Bytes)> FindKeywordLineRankedStreamingAsync(
        string filePath, List<string> keywords, CancellationToken ct)
    {
        string? best = null;
        var bestHits = 0;
        long bytes = 0;
        using var reader = new StreamReader(filePath);
        while (await reader.ReadLineAsync(ct) is { } line)
        {
            bytes += line.Length + 2; // 行字符 + 换行近似
            var hits = CountKeywordHitsInLine(line, keywords);
            if (hits > bestHits)
            {
                bestHits = hits;
                best = line.Trim();
                if (bestHits >= 5) break; // 满分档提前退出 → 免读文件剩余
            }
        }
        return (best, bestHits, bytes);
    }

    /// <summary>P4 (R330): 单行关键词命中计数 (字符串版与流式版共享, 防两处语义漂移)。</summary>
    private static int CountKeywordHitsInLine(string line, List<string> keywords)
    {
        var hits = 0;
        foreach (var kw in keywords)
        {
            if (line.Contains(kw, StringComparison.OrdinalIgnoreCase))
                hits++;
        }
        return hits;
    }


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

            // v0.11.0 R117 (真缺陷 49): Memory 源无 per-source 体积预算 — bge 真链 (R116) 后语义分
            // 带变密, 低相关 (rel~0.35) 大片段 (708tok/3snip) 整体挤进 prompt (C11 +34%)。
            // 治理: 相关性降序 → 逐段累加, 超出 per-source 预算 (500tok) 即停; rel<0.4 只保留 best 1 段。
            var ordered = results.OrderByDescending(r => r.Score).ToList();
            // R461 (命中率): per-source 预算 500 → <see cref="MemorySourceBudgetTokens"/> tok。
            // 实测 (R460 run): [Memory (RAG)] 块 197→359 字符逐轮膨胀, 是每轮**新内容** (miss) 的最大单项;
            // 每轮新内容 ≤ ~92 tok 才够 97% 命中 ⇒ 召回块必须按预算硬收。
            var budgetTokens = MemorySourceBudgetTokens;
            var usedTokens = 0;
            var keptCount = 0;
            var selected = new List<(rag.RecallResult Result, int Tokens)>();
            foreach (var result in ordered)
            {
                var approx = Math.Max(1, (result.HighlightedContent ?? result.Document.Content ?? "").Length / 3);
                if (result.Score < 0.4 && keptCount >= 1) continue; // 低相关只留 best
                if (usedTokens + approx > budgetTokens && selected.Count > 0) break; // 预算截断
                selected.Add((result, approx));
                usedTokens += approx;
                keptCount++;
            }

            foreach (var (result, _) in selected)
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
        // R129 D3: per-source 耗时可见化 (assembly 13s 定位用)
        agent.config.AgentTelemetry.Emit("phase_timing", "ContextAssembler",
            ("phase", "recall_memory"), ("ms", stopwatch.ElapsedMilliseconds));

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

            // v0.11.0 P3: 查询向量一次嵌入 (多消息复用); embedder 不可用/失败 → 纯词面 (P1 兼容)
            var queryEmbedding = await agent.contextgradient.MessageRelevanceScorer.TryEmbedQueryAsync(
                _gradientCompressor.Embedder, request.UserMessage, ct).ConfigureAwait(false);
            
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
                var relevanceScore = await CalculateMessageRelevanceAsync(
                    msg, request.UserMessage, queryEmbedding, userMessageKeywords, ct).ConfigureAwait(false);
                
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
        // R129 D3: per-source 耗时可见化
        agent.config.AgentTelemetry.Emit("phase_timing", "ContextAssembler",
            ("phase", "recall_session"), ("ms", stopwatch.ElapsedMilliseconds), ("msgs", snippets.Count));

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
            // R300 (K1 行为收益差分) + R308c (开关语义统一): DISABLE=1 或 FULL_ISOLATION=1 均跳过
            // 画像注入 (FULL_ISOLATION 隐含 DISABLE — 实验臂"全隔离"自然包含"无画像注入")。
            if (Environment.GetEnvironmentVariable("AGENTFRAMEWORK_K1_DISABLE") == "1"
                || Environment.GetEnvironmentVariable("AGENTFRAMEWORK_K1_FULL_ISOLATION") == "1")
            {
                agent.config.AgentTelemetry.Emit("tendency_bias", "ContextAssembler",
                    ("disabled", true));
                return snippets;
            }
            if (string.IsNullOrEmpty(request.UserId))
            {
                return snippets;
            }
            
            var bias = await _tendencyAnalyzer.GetContextBiasAsync(request.UserId, request.UserMessage);
            
            if (bias != null && bias.OverallConfidence > 0.3)
            {
                var content = new System.Text.StringBuilder();
                content.AppendLine("### User Profile (from history, for personalization)");
                
                if (bias.BiasScores.Any())
                {
                    // v0.11.0 R141 (K1 深化): 百分比列表对 LLM 无指导意义 —
                    // 升级为可执行行为指导 (主题→行为映射), A/B 差分实证 snip 仅 4-6tok 时 LLM 收益≈0。
                    content.AppendLine("**Observed interests (user frequently works with these):**");
                    foreach (var kvp in bias.BiasScores.OrderByDescending(x => x.Value).Take(3))
                    {
                        var hint = kvp.Key switch
                        {
                            "Python" or "python" => "prefers Python examples when giving code",
                            "Web API" or "api" => "often builds/Tests Web APIs — include endpoint examples",
                            "C#" or "csharp" or ".NET" => "prefers C#/.NET examples when giving code",
                            "test" or "测试" => "values testing — include test snippets where relevant",
                            _ => $"recently focused on {kvp.Key}",
                        };
                        content.AppendLine($"- {kvp.Key} ({kvp.Value:P0} of recent activity): {hint}");
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
            // v0.11.0 R133 (T3 观测): tendency 点位首次回答 "召回几条/被拦几条/置信多少" —
            // 断链期该源永远静默, 无打点则修复后也无法验证行为变化。
            // 注意: 仅在 analyzer 真实返回 bias 时打点 (bias==null 是 mock/未配置, 零观测价值) —
            // 无条件 Emit 会让 mock 测试每轮灌 AgentTelemetry pending ring (上限 32),
            // 与 TelemetryPendingTests 并行时挤掉 pre_boot_probe → 全仓测试 flaky (R133 实证)。
            if (bias != null)
            {
                agent.config.AgentTelemetry.Emit("phase_timing", "ContextAssembler",
                    ("phase", "recall_tendency"), ("ms", stopwatch.ElapsedMilliseconds),
                    ("user", request.UserId), ("signals", bias.BiasScores.Count),
                    ("confidence", bias.OverallConfidence), ("snippets", snippets.Count));
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Error recalling from tendency");
        }
        
        _recallCountBySource.AddOrUpdate(DataSourceType.UserTendency, stopwatch.ElapsedMilliseconds, (_, v) => v + stopwatch.ElapsedMilliseconds);
        
        return snippets;
    }
}
