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

    private async Task<List<ContextSnippet>> CompressSnippetsAsync(
        List<ContextSnippet> snippets,
        Dictionary<DataSourceType, int> allocation,
        ContextAssemblyRequest request,
        CancellationToken ct)
    {
        var compressed = new List<ContextSnippet>();
        // R129 D3: 压缩段总耗时
        var compressSw = System.Diagnostics.Stopwatch.StartNew();
        
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
                string compressedContent;
                agent.contextgradient.GradientResult? gradient = null;
                if (!_compressionBreaker.AllowAttempt)
                {
                    // v0.13.3 D4 熔断中: 直通原文 (M1 降级链终点), 打点
                    agent.config.AgentTelemetry.Emit("compression_breaker", "ContextAssembler",
                        ("state", "open"), ("action", "passthrough"));
                    snippet.CompressedContent = snippet.Content;
                    snippet.IsCompressed = false;
                    continue;
                }
                try
                {
                    gradient = await _gradientCompressor.CompressAsync(new agent.contextgradient.GradientRequest
                    {
                        Content = snippet.Content,
                        RelevanceScore = snippet.RelevanceScore,
                        TokenBudget = quota / Math.Max(1, snippets.Count(s => s.SourceType == snippet.SourceType)),
                        AnchorWords = anchors,
                    });
                    compressedContent = gradient.DriftCheckPassed || gradient.Level == agent.contextgradient.GradientLevel.Full
                        ? gradient.Content
                        : snippet.Content; // 漂移校验失败且非全文 → 保原文 (宁大不歪)
                }
                catch (Exception ex) when (ex is not OperationCanceledException)
                {
                    // v0.13.3 D1 (用户问询驱动: 压缩失败后续防护): 压缩器异常 (bge 崩/LLama 异常)
                    // 不再炸整轮组装 — 该 snippet 回退原文 + error 打点 (M1 分级降级链第一环)。
                    agent.config.AgentTelemetry.Emit("compression_error", "ContextAssembler",
                        ("source", snippet.SourceType.ToString()),
                        ("ex_type", ex.GetType().Name),
                        ("msg", ex.Message.Length > 80 ? ex.Message[..80] : ex.Message));
                    compressedContent = snippet.Content;
                }

                snippet.CompressedContent = compressedContent;
                snippet.IsCompressed = compressedContent != snippet.Content;
                snippet.EstimatedTokens = await _tokenCompressor.CountTokensAsync(compressedContent);
                // v0.11.0: 压缩打点 (压缩率对比数据 — level/漂移校验/语义相似度/前后字符)
                if (gradient is not null)
                {
                    agent.config.AgentTelemetry.Emit("compression", "ContextGradientCompressor",
                        ("level", (int)gradient.Level),
                        ("drift_ok", gradient.DriftCheckPassed),
                        ("semantic", gradient.SemanticSimilarity is { } sem ? Math.Round(sem, 3) : -1),
                        ("chars", gradient.OriginalChars + "->" + gradient.CompressedChars));
                    // v0.13.3 D2: 哨兵丢失打点 (关键信息校验 — semantic 盲区补丁)
                    if (gradient.SentinelLosses.Count > 0)
                        agent.config.AgentTelemetry.Emit("compression_sentinel", "ContextAssembler",
                            ("lost_n", gradient.SentinelLosses.Count),
                            ("samples", string.Join(",", gradient.SentinelLosses.Take(3))),
                            ("level", (int)gradient.Level));
                    // v0.13.3 D4: 熔断器记录 — 哨兵丢失也计失败 (关键信息丢失 = 压缩失败语义)
                    _compressionBreaker.Record(gradient.SentinelLosses.Count == 0);
                }
            }
            
            compressed.Add(snippet);
        }
        compressSw.Stop();
        agent.config.AgentTelemetry.Emit("phase_timing", "ContextAssembler",
            ("phase", "compress"), ("ms", compressSw.ElapsedMilliseconds), ("n", snippets.Count));

        return compressed;
    }
}
