using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;

public sealed partial class ModelQueueRouter : IModelQueueCaller
{

    private async Task<QueueResponse> OnTransientFailureAsync(
        ModelCatalogEntry entry, QueuePrompt prompt, TaskKindHint kind, string intent,
        CancellationToken ct, string why, int attempt = 1)
    {
        // v0.11.0 R23 修复 (真 bug 21): 原"连续失败"计数跨请求, 单请求瞬态失败 (超时/网络抖动)
        // 直接报错给用户且从不切备 — failover 名存实亡 (实测 C03 三子任务超时 101s 后空手而归)。
        // 现策略: 同请求内 ①同模型重试 1 次 (attempt 1→2) ②仍败切备选模型重试 1 次 ③备选也败才返回失败。
        if (attempt <= 2)
        {
            // v0.13.3 R242 (KPI-2 优化①, audit 数据驱动): 429 限流 = 速率窗口问题, 窗口内同模型
            // 重试必再 429 (直探 429/20s 交替实证) 且重发全 prompt (~1000 tok/次浪费, KPI-2 报告:
            // C07 2355 tok 中 ~1000 是重试链)。改为: 429 跳过同模型重试直接进切备链 —
            // 备模型不同 key/端点, 不受该窗口影响。非 429 瞬态 (网络/超时) 仍同模型重试。
            if (why.Contains("429") || why.Contains("Too Many Requests"))
            {
                agent.config.AgentTelemetry.Emit("llm_retry", "ModelQueueRouter",
                    ("model", entry.Id), ("attempt", attempt), ("why", why), ("skipped", true));
                return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, why + " (429 跳过同模型重试)", attempt + 2)
                    .ConfigureAwait(false);
            }
            _logger.LogWarning("ModelQueue: {Model} 瞬态失败 ({Why}) — 请求内重试 {Attempt}/2", entry.Id, why, attempt);
            agent.config.AgentTelemetry.Emit("llm_retry", "ModelQueueRouter",
                ("model", entry.Id), ("attempt", attempt), ("why", why));
            try
            {
                // v0.12.0 R223 (真缺陷 65): 请求内重试成功路径此前不补 llm_call 打点 —
                // bigmodel 429/瞬态 首调失败→重试成功时, telemetry 只剩失败点 (ms≈200/tokens=0),
                // KPI tok/case 被系统性低估 (批187 实测 7/9 用例首调 429 → 126/case 假性 KPI_BREACH)。
                // 补成功打点 (attempt=2) — 用量/耗时/模型三观与主成功路径对齐。
                var retrySw = System.Diagnostics.Stopwatch.StartNew();
                var retried = await CallEntryAsync(entry, prompt, ct).ConfigureAwait(false);
                retrySw.Stop();
                if (retried.Success)
                {
                    lock (_lock) _consecutiveFailures = 0;
                    LastSelectionBasis = $"retry_ok:{entry.Id} (attempt {attempt + 1})";
                    _tokenUsage?.RecordUsage(retried.Model, entry.Provider, retried.PromptTokens, retried.CompletionTokens);
                    var cacheKv = PromptCacheKpi.Fields(retried.CacheHitTokens, retried.CacheMissTokens);
                    // R380: 重试路径同样只算"需要命中的部分" (否则 KPI 漏掉重试调用)
                    var effKv = PromptCacheKpi.EffectiveFields(retried.CacheHitTokens, retried.PromptTokens, LastPromptTokensFor(prompt.SessionId));
                    var chanKv = PromptCacheKpi.ChannelFields(retried.CacheHitTokens, retried.CacheMissTokens, retried.PromptTokens, LastPromptTokensFor(prompt.SessionId));
                    var bandKv2 = PromptCacheRedline.BandFields(prompt.TurnIndex, (int)(effKv[0].Value ?? 0), retried.PromptTokens, (double)(effKv[1].Value ?? -1d));
                    agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                        ("model", entry.Id), ("provider", entry.Provider),
                        ("prompt_tokens", retried.PromptTokens), ("completion_tokens", retried.CompletionTokens),
                        ("total_tokens", retried.TokensUsed), ("success", true),
                        ("content_len", retried.Content?.Length ?? 0),
                        ("reasoning_len", retried.ReasoningContent?.Length ?? 0),
                        ("ms", retrySw.ElapsedMilliseconds), ("attempt", attempt + 1),
                        cacheKv[0], cacheKv[1], cacheKv[2], effKv[0], effKv[1], chanKv[0], chanKv[1], chanKv[2],
                        bandKv2[0], bandKv2[1], bandKv2[2], bandKv2[3], bandKv2[4], bandKv2[5], bandKv2[6]);
                    return retried;
                }
                // 软失败 (Success=false 但未抛异常) 也算本次失败, 继续走切备
                return await OnTransientFailureAsync(entry, prompt, kind, intent, ct,
                    retried.Error ?? "重试仍失败", attempt + 1).ConfigureAwait(false);
            }
            catch (HttpRequestException ex2)
            {
                return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, $"重试网络错误: {ex2.Message}", attempt + 1).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, "重试超时", attempt + 1).ConfigureAwait(false);
            }
        }

        // 重试耗尽 → 切备选模型链 (v0.13.1 F1 用户钦定: 存在备选时启用兜底服务,
        // 逐个按性价比序 (cost_quality=auto 同源判据: 质量档降序, 同档低价优先; catalog=旧目录序)
        // 失败兜底, 每个兜底回复过 FallbackConfig.VerifyReply 校验; 校验失败继续链内下一个 —
        // 最多 PerRequestMaxFallbacks 个。capability 硬过滤语义不变 (R226 文本优先 / R227 硬过滤)。
        lock (_lock) _consecutiveFailures++;
        List<ModelCatalogEntry> backupChain;
        lock (_lock)
        {
            var candidates = _catalog.Models.Where(m =>
                !string.Equals(m.Id, entry.Id, StringComparison.OrdinalIgnoreCase) &&
                (prompt.ImageUrls.Count > 0 ? m.Capabilities.ImageInput : m.Capabilities.Text) &&
                (m.ApiKeyEnv is null ||
                 !string.IsNullOrEmpty(Environment.GetEnvironmentVariable(m.ApiKeyEnv))));
            if (string.Equals(_fallback.Order, "cost_quality", StringComparison.OrdinalIgnoreCase))
                candidates = candidates
                    .OrderByDescending(m => m.Capabilities.ImageInput == false)
                    .ThenByDescending(m => m.ReasoningScore + m.CodingScore)
                    .ThenBy(m => m.PriceInPerM + m.PriceOutPerM);
            backupChain = candidates.Take(_fallback.PerRequestMaxFallbacks).ToList();
        }
        QueueResponse? lastFail = null;
        foreach (var backup in backupChain)
        {
            var attemptN = backupChain.IndexOf(backup) + 1;
            _logger.LogWarning("ModelQueue: {From} 重试耗尽 → 切备 {To} (兜底链 {N}/{Max})",
                entry.Id, backup.Id, attemptN, backupChain.Count);
            agent.config.AgentTelemetry.Emit("fallback_attempt", "ModelQueueRouter",
                ("from", entry.Id), ("to", backup.Id),
                ("attempt_n", attemptN), ("chain_size", backupChain.Count), ("why", why));
            try
            {
                var backupSw = System.Diagnostics.Stopwatch.StartNew();
                var backupResp = await CallEntryAsync(backup, prompt, ct).ConfigureAwait(false);
                backupSw.Stop();
                // v0.13.1 F1 兜底校验: 失败 = 此备选无效 → 继续下一个 (用户钦定"逐个...兜底"):
                if (_fallback.VerifyReply(backupResp))
                {
                    lock (_lock)
                    {
                        Switches.Add(new ModelSwitchRecord
                            { From = entry.Id, To = backup.Id, Reason = "transient_failover" });
                        _activeModelId = backup.Id;
                        _manualOverride = null;
                        _consecutiveFailures = 0;
                        LastSelectionBasis = $"failover:{backup.Id} (原 {entry.Id} 瞬态失败, 兜底 {attemptN}/{backupChain.Count})";
                    }
                    _tokenUsage?.RecordUsage(backupResp.Model, backup.Provider, backupResp.PromptTokens, backupResp.CompletionTokens);
                    var cacheKv = PromptCacheKpi.Fields(backupResp.CacheHitTokens, backupResp.CacheMissTokens);
                    // R380: 备选 provider 路径同样只算"需要命中的部分"
                    var effKv = PromptCacheKpi.EffectiveFields(backupResp.CacheHitTokens, backupResp.PromptTokens, LastPromptTokensFor(prompt.SessionId));
                    var chanKv = PromptCacheKpi.ChannelFields(backupResp.CacheHitTokens, backupResp.CacheMissTokens, backupResp.PromptTokens, LastPromptTokensFor(prompt.SessionId));
                        var bandKv2 = PromptCacheRedline.BandFields(prompt.TurnIndex, (int)(effKv[0].Value ?? 0), backupResp.PromptTokens, (double)(effKv[1].Value ?? -1d));
                    agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                        ("model", backup.Id), ("provider", backup.Provider),
                        ("prompt_tokens", backupResp.PromptTokens), ("completion_tokens", backupResp.CompletionTokens),
                        ("total_tokens", backupResp.TokensUsed), ("success", true),
                        ("content_len", backupResp.Content?.Length ?? 0),
                        ("reasoning_len", backupResp.ReasoningContent?.Length ?? 0),
                        ("ms", backupSw.ElapsedMilliseconds), ("attempt", "failover"),
                        cacheKv[0], cacheKv[1], cacheKv[2], effKv[0], effKv[1], chanKv[0], chanKv[1], chanKv[2],
                        bandKv2[0], bandKv2[1], bandKv2[2], bandKv2[3], bandKv2[4], bandKv2[5], bandKv2[6]);
                    return backupResp;
                }
                agent.config.AgentTelemetry.Emit("fallback_verify_fail", "ModelQueueRouter",
                    ("model", backup.Id), ("success", backupResp.Success),
                    ("content_len", backupResp.Content?.Length ?? 0));
                lastFail = backupResp.Success ? null : backupResp;
                if (lastFail is null)
                    lastFail = new QueueResponse { Success = false, Error = $"备选 {backup.Id} 回复未通过兜底校验", Model = backup.Id };
            }
            catch (Exception ex3) when (ex3 is HttpRequestException
                || (ex3 is OperationCanceledException oce && !ct.IsCancellationRequested))
            {
                lastFail = new QueueResponse
                {
                    Success = false,
                    Error = $"备选 {backup.Id} 失败: {ex3.Message}",
                    Model = backup.Id,
                };
            }
        }
        if (lastFail is not null)
        {
            // 兜底链耗尽 — 如实返回最后失败 (不降级硬跑):
            return lastFail;
        }

        // v0.11.0 R23: 重试耗尽且无可用备选 — 保守计数后如实返回失败
        lock (_lock)
        {
            _consecutiveFailures++;
            LastSelectionBasis = $"primary:{entry.Id} (重试耗尽, 无可用备选: {why})";
        }
        return new QueueResponse
        {
            Success = false,
            Error = $"模型 {entry.Id} 调用失败 (请求内重试+备选均不可用): {why}",
            Model = entry.Id,
        };
    }

    /// <summary>
    /// v0.10.0 余额不足备选: 同目录排除当前模型, 按 (余额充足, 分数) 选最优。
    /// 本地通道可用 → 本地优先 (无余额概念, 天然充足)。
    /// </summary>
    private ModelCatalogEntry? SelectAlternativeByBalance(ModelCatalogEntry current, int estimatedTokens)
    {
        if (_tokenUsage is null) return null;
        var candidates = _catalog.Models
            .Where(m => !string.Equals(m.Id, current.Id, StringComparison.OrdinalIgnoreCase))
            // v0.11.0 R115 (真缺陷 46): 候选必须 key 已配置 (曾选中 claude-sonnet-4-5 而
            // ANTHROPIC_KEY 未设 → 切换后调用必败, 比不切更糟)
            .Where(m => !string.IsNullOrEmpty(Environment.GetEnvironmentVariable(m.ApiKeyEnv)))
            .Select(m => (Model: m, Est: _tokenUsage!.EstimateBalance(m.Provider, estimatedTokens)))
            .Where(t => t.Est.Sufficient)
            .OrderByDescending(t => t.Model.ReasoningScore + t.Model.CodingScore)
            .ToList();
        return candidates.Count == 0 ? null : candidates[0].Model;
    }

    /// <summary>
    /// 通道优先级选模 (R351: 本地/官方通道移除 — 纯远端目录选优)。
    /// 通道满 (AcquireChannel=null) → 不阻塞主链, 退回目录首模型由其自身失败语义兜底。
    /// </summary>
    private ModelCatalogEntry? SelectByChannelPriority(TaskKindHint kind, string intent, int estimatedTokens)
    {
        var remoteRanked = Scheduler.RankCandidates(_catalog.Models, kind, estimatedTokens);
        if (remoteRanked.Count == 0)
            return null;
        LastSelectionBasis = $"channel:remote:{remoteRanked[0].Model.Id}";
        return remoteRanked[0].Model;
    }

    /// <summary>按目录条目真实调用 OpenAI 兼容 chat completions (endpoint/keyEnv 来自目录)</summary>

    /// <summary>
    /// v0.12.0 A2: 请求序列化 — 无 parts 走 source-gen (原路); 任一消息 HasParts → 手写
    /// Utf8JsonWriter 输出 parts[] 形态 (source-gen 对 union 不友好, 手写 AOT 安全)。
    /// </summary>
    internal static string SerializeChatRequest(QueueChatRequest request)
    {
        // R456: 工具声明/回灌消息必须走手写 writer (source-gen DTO 不含这两个字段);
        // 无工具请求仍走 source-gen ⇒ 与旧版逐字节相同 (缓存前缀不受影响)。
        var manual = !string.IsNullOrEmpty(request.ToolsJson) || request.Messages.Any(m => m.HasParts || m.HasToolPayload);
        if (!manual)
            return JsonSerializer.Serialize(request, ModelQueueJsonContext.Default.QueueChatRequest);
        using var ms = new System.IO.MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteString("model", request.Model);
            w.WritePropertyName("messages");
            w.WriteStartArray();
            foreach (var m in request.Messages)
            {
                w.WriteStartObject();
                w.WriteString("role", m.Role);
                if (m.HasParts)
                {
                    w.WritePropertyName("content");
                    w.WriteStartArray();
                    foreach (var p in m.ContentParts!)
                    {
                        w.WriteStartObject();
                        w.WriteString("type", p.Type);
                        if (p.Type == "text")
                            w.WriteString("text", p.Text ?? string.Empty);
                        else if (p.Type == "image_url" && p.ImageUrl != null)
                        {
                            w.WritePropertyName("image_url");
                            w.WriteStartObject();
                            w.WriteString("url", p.ImageUrl.Url);
                            w.WriteEndObject();
                        }
                        w.WriteEndObject();
                    }
                    w.WriteEndArray();
                }
                else if (m.ToolCalls is { Count: > 0 })
                {
                    // assistant 请求工具: content 省略 (协议允许), 只带 tool_calls
                }
                else
                {
                    w.WriteString("content", m.Content);
                }
                if (m.ToolCalls is { Count: > 0 })
                {
                    w.WritePropertyName("tool_calls");
                    w.WriteStartArray();
                    foreach (var tc in m.ToolCalls)
                    {
                        w.WriteStartObject();
                        w.WriteString("id", tc.Id);
                        w.WriteString("type", "function");
                        w.WritePropertyName("function");
                        w.WriteStartObject();
                        w.WriteString("name", tc.Name);
                        w.WriteString("arguments", tc.ArgumentsJson);
                        w.WriteEndObject();
                        w.WriteEndObject();
                    }
                    w.WriteEndArray();
                }
                if (!string.IsNullOrEmpty(m.ToolCallId))
                    w.WriteString("tool_call_id", m.ToolCallId);
                w.WriteEndObject();
            }
            w.WriteEndArray();
            if (!string.IsNullOrEmpty(request.ToolsJson))
            {
                w.WritePropertyName("tools");
                w.WriteRawValue(request.ToolsJson, skipInputValidation: true);
            }
            if (!string.IsNullOrEmpty(request.ReasoningEffort))
            {
                w.WriteString("reasoning_effort", request.ReasoningEffort);
            }
            w.WriteEndObject();
        }
        return System.Text.Encoding.UTF8.GetString(ms.ToArray());
    }

    /// <summary>R371: 空正文恢复时的输出预算 (×4 于默认 8192; 硬上限保护, 不是"再抬天花板"而是配合抑制推理)。</summary>
    private const int MaxTokensEscalated = 32768;

    /// <summary>默认输出预算 (与 DTO 默认一致; 只作截断保护, 实际长度由输出纪律约束)。</summary>
    public const int DefaultMaxTokens = 8192;
}
