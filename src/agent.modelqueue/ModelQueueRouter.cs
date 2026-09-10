using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;

/// <summary>队列调用请求 (协议自洽 — 不依赖 agent 主程序集, adapter 负责转换)</summary>
public sealed class QueuePrompt
{
    public string SystemPrompt { get; set; } = string.Empty;
    public string ContextPrompt { get; set; } = string.Empty;

    /// <summary>(role, content) 历史</summary>
    public List<QueueHistoryMessage> History { get; set; } = new();
    public string UserMessage { get; set; } = string.Empty;

    /// <summary>预估输入 token (费用估算/选模)</summary>
    public int EstimatedTokens { get; set; }

    /// <summary>v0.11.0 R22: 推理档位建议 (null=默认深推理; low=轻思考)。</summary>
    public string? ReasoningEffort { get; set; }

    /// <summary>v0.12.0 A2: 图像附件 (URL/base64 data URL) — 非空时路由强制云端 + user 消息 parts[] 形态。</summary>
    public List<string> ImageUrls { get; set; } = new();
    public int ImageCount => ImageUrls.Count;
}

public sealed class QueueHistoryMessage
{
    public string Role { get; set; } = "user";
    public string Content { get; set; } = string.Empty;
}

/// <summary>队列调用响应 (协议自洽)</summary>
public sealed class QueueResponse
{
    public string Content { get; set; } = string.Empty;
    public bool Success { get; set; } = true;
    public string? Error { get; set; }
    public string Model { get; set; } = "unknown";
    public int PromptTokens { get; set; }
    public int TokensUsed { get; set; }

    /// <summary>v0.10.0: 输出 token 数 (TokensUsed = prompt + completion)</summary>
    public int CompletionTokens => Math.Max(0, TokensUsed - PromptTokens);
}

/// <summary>模型队列调用端口 (adapter 在 agent 主程序集实现 ILLMCaller 时消费)</summary>
public interface IModelQueueCaller
{
    Task<QueueResponse> CallAsync(QueuePrompt prompt, TaskKindHint kind, string intent, CancellationToken ct = default);
}

/// <summary>模型切换审计事件 (C.4: 自动切换记录切换事件, /status JSON 可读)</summary>
public sealed class ModelSwitchRecord
{
    public string From { get; set; } = string.Empty;
    public string To { get; set; } = string.Empty;

    /// <summary>切换原因 (consecutive_failures / manual / cost_routing)</summary>
    public string Reason { get; set; } = string.Empty;

    public DateTime At { get; set; } = DateTime.UtcNow;
}

/// <summary>
/// 模型队列路由器 (v7.15 C.3.3): ILLMCaller 实现 — 内部按策略从模型目录选模型,
/// 主模型连续失败 N 次自动切备 (取消永不触发切换), 手动 /model 指定最高优先。
/// 序列化全走 source-gen fast-path (AOT 铁律)。
/// </summary>
public sealed class ModelQueueRouter : IModelQueueCaller
{
    private readonly ModelCatalog _catalog;
    private readonly ModelSelectionPolicy _policy;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly Microsoft.Extensions.Logging.ILogger _logger;
    private readonly TokenUsageService? _tokenUsage;
    private readonly FallbackConfig _fallback;

    /// <summary>R115 (缺陷 43): 余额快照惰性 fire-once 同步器 (进程内仅一次)</summary>
    private sealed class LazyBalanceSync
    {
        private Task? _task;
        private readonly object _lock = new();

        public Task EnsureStartedAsync(TokenUsageService service)
        {
            lock (_lock)
            {
                _task ??= Task.Run(async () =>
                {
                    try { await service.InitializeAsync().ConfigureAwait(false); }
                    catch { /* 初始化失败不阻断 — 余额未知不判定语义 */ }
                });
                return _task;
            }
        }
    }

    private readonly LazyBalanceSync _balanceSyncOnce = new();

    /// <summary>通道调度 (R351: 仅远端目录通道; 本地/官方已移除 — 用户钦定全 API 化)</summary>
    public ChannelScheduler Scheduler { get; }

    /// <summary>手动覆盖 (null = 自动); /model &lt;id&gt; 设置, /model auto 清除</summary>
    private string? _manualOverride;

    /// <summary>当前活跃模型 (自动粘性: 失败切换后固定到新模型, 成功不回切)</summary>
    private string? _activeModelId;

    private int _consecutiveFailures;
    public const int MaxConsecutiveFailures = 3;

    /// <summary>切换审计 (面板/CLI 可读)</summary>
    public List<ModelSwitchRecord> Switches { get; } = new();

    /// <summary>上一次选模依据 (审计/调试)</summary>
    public string LastSelectionBasis { get; private set; } = "init";

    private readonly object _lock = new();

    public ModelQueueRouter(
        ModelCatalog catalog,
        IHttpClientFactory httpClientFactory,
        Microsoft.Extensions.Logging.ILogger logger,
        ChannelScheduler? scheduler = null,
        TokenUsageService? tokenUsage = null,
        FallbackConfig? fallbackConfig = null)
    {
        _fallback = fallbackConfig ?? new FallbackConfig();
        _catalog = catalog;
        _policy = new ModelSelectionPolicy();
        _httpClientFactory = httpClientFactory;
        _logger = logger;
        _tokenUsage = tokenUsage;
        Scheduler = scheduler ?? new ChannelScheduler();
    }

    /// <summary>当前手动覆盖模型 id (null = auto 自动选模模式) — /model 指令与 /status 展示</summary>
    public string? ManualOverride => _manualOverride;

    /// <summary>v0.10.0: 最近一次余额不足提示 (model:xxx flags:余额不足 协议 — 前端展示用)</summary>
    public string? LastBalanceFlag { get; private set; }

    /// <summary>模型目录 (只读暴露: /model list 序号化列表的数据源)</summary>
    public ModelCatalog Catalog => _catalog;

    /// <summary>当前活跃模型条目 (null = 目录空)</summary>
    public ModelCatalogEntry? ActiveModel
    {
        get
        {
            lock (_lock)
            {
                return _catalog.Find(_manualOverride ?? _activeModelId) ?? _catalog.Models.FirstOrDefault();
            }
        }
    }

    /// <summary>手动指定模型 (返回 false = 目录无此 id); id="auto" 恢复自动</summary>
    public bool SetManualOverride(string? modelId)
    {
        lock (_lock)
        {
            if (modelId is null || modelId.Equals("auto", StringComparison.OrdinalIgnoreCase))
            {
                if (_manualOverride != null)
                    Switches.Add(new ModelSwitchRecord
                        { From = _manualOverride, To = "auto", Reason = "manual" });
                _manualOverride = null;
                _activeModelId = null; // 清粘性: auto = 完全回到自动 (粘性只在失败切换时重建)
                _consecutiveFailures = 0;
                return true;
            }
            var entry = _catalog.Find(modelId);
            if (entry is null)
                return false;
            var prev = _manualOverride ?? _activeModelId ?? "(auto)";
            _manualOverride = entry.Id;
            _activeModelId = entry.Id;
            _consecutiveFailures = 0;
            Switches.Add(new ModelSwitchRecord { From = prev, To = entry.Id, Reason = "manual" });
            LastSelectionBasis = $"manual:{entry.Id}";
            return true;
        }
    }

    public async Task<QueueResponse> CallAsync(QueuePrompt prompt, TaskKindHint kind, string intent, CancellationToken ct = default)
    {
        // R351 (用户钦定): 本地推理通道移除 — 全部经 API 调用 (远端目录)。
        // 需求1 混合调度: 手动/粘性优先 → 通道优先级 (远端目录)
        var entry = _catalog.Find(_manualOverride ?? _activeModelId)
                    ?? _policy.Select(null, kind, intent,
                        prompt.EstimatedTokens, prompt.EstimatedTokens / 3, _catalog)
                    ?? SelectByChannelPriority(kind, intent, prompt.EstimatedTokens);
        if (entry is null)
        {
            return new QueueResponse
            {
                Success = false,
                Error = "模型目录为空: 请在 config/base/models.yaml 配置至少一个模型",
            };
        }

        // v0.12.0 A3 (真缺陷 64): 带图请求必须落在 image_input 模型 —
        // 手动/粘性/策略选中 text-only 模型 (glm-4-plus/deepseek 等) 时重路由到首个可用视觉模型
        // (视觉模型 key 可用性同 policy 判据; 无视觉候选 → 保持原 entry, 让 API 错误如实暴露)。
        if (prompt.ImageUrls.Count > 0 && !entry.Capabilities.ImageInput)
        {
            var vision = _catalog.Models.FirstOrDefault(m =>
                m.Capabilities.ImageInput &&
                (m.ApiKeyEnv is null ||
                 !string.IsNullOrEmpty(Environment.GetEnvironmentVariable(m.ApiKeyEnv))));
            if (vision is not null)
            {
                Switches.Add(new ModelSwitchRecord
                    { From = entry.Id, To = vision.Id, Reason = "vision_required" });
                LastSelectionBasis = $"vision_required:{vision.Id} (原 {entry.Id} 无 image_input, 带图请求)";
                _logger.LogWarning("ModelQueue: {From} 无 image_input 且请求带图 → 重路由 {To}", entry.Id, vision.Id);
                entry = vision;
            }
        }

        // v0.11.0 R115 (真缺陷 43): TokenUsageService.InitializeAsync 此前无调用点 — 余额快照
        // 恒空 → EstimateBalance 恒 (null,true) → MIN_BALANCE 阈值切模整条链路死代码。
        // 惰性 fire-once 启动同步 (后台, 不阻断首调用; 失败静默走"余额未知不判定"语义)。
        if (_tokenUsage is not null)
        {
            var syncTask = _balanceSyncOnce.EnsureStartedAsync(_tokenUsage);
            try { await syncTask.WaitAsync(TimeSpan.FromSeconds(3), ct).ConfigureAwait(false); }
            catch (TimeoutException) { /* 首同步 >3s 不阻断对话, 本轮按余额未知处理 */ }
        }

        // v0.10.0: 余额预估检查 — 不足 → 切换其他模型 + flags:余额不足 提示
        if (_tokenUsage is not null)
        {
            var (remaining, sufficient) = _tokenUsage.EstimateBalance(entry.Provider, prompt.EstimatedTokens);
            if (!sufficient)
            {
                var alt = SelectAlternativeByBalance(entry, prompt.EstimatedTokens);
                if (alt is not null && alt.Id != entry.Id)
                {
                    Switches.Add(new ModelSwitchRecord
                        { From = entry.Id, To = alt.Id, Reason = "insufficient_balance" });
                    _activeModelId = alt.Id;
                    LastSelectionBasis = $"balance_fallback:{alt.Id} ({entry.Id} 余额不足)";
                    LastBalanceFlag = $"model:{alt.Id} flags:余额不足 (原 {entry.Id} 预估余额 ${remaining:F2})";
                    _logger.LogWarning("ModelQueue: {From} 余额不足 (${Remain:F2}) → 切换 {To}",
                        entry.Id, remaining ?? 0, alt.Id);
                    entry = alt;
                }
                else
                {
                    // 无备选 → 继续原模型但带上提示
                    LastBalanceFlag = $"model:{entry.Id} flags:余额不足 (预估剩余 ${remaining:F2}, 无备选继续)";
                    _logger.LogWarning("ModelQueue: {Id} 余额不足但无备选 — 继续原模型", entry.Id);
                }
            }
        }

        // v0.11.0 R129 (PGO v2 D3): 热路径计时 — llm_call 真耗时 (成功/失败均打), 与 wall 的差值
        // 即排队/路由开销; 依据 assembly 打点既有 ms 风格 (IndustrialAgentV2.cs:383)。
        var llmSw = System.Diagnostics.Stopwatch.StartNew();
        try
        {
            var resp = await CallEntryAsync(entry, prompt, ct);
            llmSw.Stop();
            lock (_lock)
            {
                _consecutiveFailures = 0;
                // v0.11.0 R89 (真缺陷 36): auto 选模成功后同步粘性 id — 原 _activeModelId 只在
                // failover/手动切换时更新, /model 与 /balance 查询时 ActiveModel getter
                // 落到目录首项 (gpt-4o), 与实际调用模型 (glm) 不一致 (真机 /model 实证)。
                if (_manualOverride is null) _activeModelId = entry.Id;
            }
            // v0.10.0: 用量本地累计
            _tokenUsage?.RecordUsage(resp.Model, entry.Provider, resp.PromptTokens, resp.CompletionTokens);
            agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                ("model", entry.Id), ("provider", entry.Provider),
                ("prompt_tokens", resp.PromptTokens), ("completion_tokens", resp.CompletionTokens),
                ("total_tokens", resp.TokensUsed), ("success", true),
                // v0.11.0 R19: 内容长度诊断 (C03 曾现 completion 2000 tok 但回复渲染空 — 定位内容丢在链路哪段)
                ("content_len", resp.Content?.Length ?? 0),
                // v0.11.0 R129 (D3): LLM 真耗时 ms
                ("ms", llmSw.ElapsedMilliseconds));
            // 阈值再同步 (fire-and-forget, 不阻塞主链)
            if (_tokenUsage is not null && _tokenUsage.NeedsResync(entry.Provider))
                _ = _tokenUsage.TryResyncAsync(entry.Provider, CancellationToken.None);
            return resp;
        }
        catch (HttpRequestException ex)
        {
            llmSw.Stop();
            agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                ("model", entry.Id), ("provider", entry.Provider), ("success", false), ("error_kind", "http"), ("error", ex.Message),
                ("ms", llmSw.ElapsedMilliseconds));
            return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, $"网络错误: {ex.Message}").ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            // HttpClient 超时 (非用户取消) = 瞬态
            llmSw.Stop();
            agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                ("model", entry.Id), ("provider", entry.Provider), ("success", false), ("error_kind", "timeout"),
                ("ms", llmSw.ElapsedMilliseconds));
            return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, "请求超时").ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            // 用户取消永不触发模型切换 (C.4 验收)
            throw;
        }
    }

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
                    agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                        ("model", entry.Id), ("provider", entry.Provider),
                        ("prompt_tokens", retried.PromptTokens), ("completion_tokens", retried.CompletionTokens),
                        ("total_tokens", retried.TokensUsed), ("success", true),
                        ("content_len", retried.Content?.Length ?? 0),
                        ("ms", retrySw.ElapsedMilliseconds), ("attempt", attempt + 1));
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
                    agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                        ("model", backup.Id), ("provider", backup.Provider),
                        ("prompt_tokens", backupResp.PromptTokens), ("completion_tokens", backupResp.CompletionTokens),
                        ("total_tokens", backupResp.TokensUsed), ("success", true),
                        ("content_len", backupResp.Content?.Length ?? 0),
                        ("ms", backupSw.ElapsedMilliseconds), ("attempt", "failover"));
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
    private static string SerializeChatRequest(QueueChatRequest request)
    {
        if (!request.Messages.Any(m => m.HasParts))
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
                else
                {
                    w.WriteString("content", m.Content);
                }
                w.WriteEndObject();
            }
            w.WriteEndArray();
            if (!string.IsNullOrEmpty(request.ReasoningEffort))
            {
                w.WriteString("reasoning_effort", request.ReasoningEffort);
            }
            w.WriteEndObject();
        }
        return System.Text.Encoding.UTF8.GetString(ms.ToArray());
    }

    private async Task<QueueResponse> CallEntryAsync(ModelCatalogEntry entry, QueuePrompt prompt, CancellationToken ct)
    {
        // R351: 全通道 key 走环境变量 (官方内存通道已移除; 凭据铁律不变)
        var apiKey = Environment.GetEnvironmentVariable(entry.ApiKeyEnv);
        if (string.IsNullOrEmpty(apiKey))
        {
            return new QueueResponse
            {
                Success = false,
                Model = entry.Id,
                Error = $"环境变量 {entry.ApiKeyEnv} 未设置 (模型 {entry.Id} 的 API Key 来源)",
            };
        }

        var client = _httpClientFactory.CreateClient("modelqueue");
        var messages = new List<QueueChatMessage>();
        if (!string.IsNullOrEmpty(prompt.SystemPrompt))
            messages.Add(new QueueChatMessage { Role = "system", Content = prompt.SystemPrompt });
        if (!string.IsNullOrEmpty(prompt.ContextPrompt))
            messages.Add(new QueueChatMessage
            {
                Role = "system",
                Content = $"以下是你可以参考的相关上下文信息，请结合这些信息回答用户问题：\n\n{prompt.ContextPrompt}"
            });
        foreach (var msg in prompt.History)
            messages.Add(new QueueChatMessage { Role = msg.Role, Content = msg.Content });
        // v0.12.0 A2: 带图 user 消息 → parts[] 多段 (text + image_url × N)
        if (prompt.ImageUrls.Count > 0)
        {
            var parts = new List<QueueContentPart> { new() { Type = "text", Text = prompt.UserMessage } };
            // v0.12.0 A3 (真缺陷 63): 本地路径 → base64 data URL (云端无法读本地文件, 真机 400/1210 实证)
            parts.AddRange(prompt.ImageUrls.Select(u => new QueueContentPart
            {
                Type = "image_url",
                ImageUrl = new QueueImageUrl { Url = VisionPayload.ToDataUrl(u) },
            }));
            messages.Add(new QueueChatMessage { Role = "user", Content = prompt.UserMessage, ContentParts = parts });
        }
        else
        {
            messages.Add(new QueueChatMessage { Role = "user", Content = prompt.UserMessage });
        }

        // v0.12.0 A3 (真缺陷 64): coding 端点不收图像 (HTTP 400 1210 真机实证) —
        // 带图请求改写标准 v4 chat 端点 (glm-5.3-flash 视觉走 v4, data URL 真机已验 1445tok)。
        var targetEndpoint = prompt.ImageUrls.Count > 0 ? VisionPayload.ToChatEndpoint(entry.Endpoint) : entry.Endpoint;
        var request = new QueueChatRequest { Model = entry.Id, Messages = messages, ReasoningEffort = prompt.ReasoningEffort };
        using var http = new HttpRequestMessage(HttpMethod.Post, targetEndpoint)
        {
            Content = new StringContent(
                SerializeChatRequest(request),
                System.Text.Encoding.UTF8, "application/json"),
        };
        http.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", apiKey);

        using var resp = await client.SendAsync(http, ct);
        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            throw new HttpRequestException($"HTTP {(int)resp.StatusCode}: {Truncate(body, 200)}");
        }

        var parsed = JsonSerializer.Deserialize(body, ModelQueueJsonContext.Default.OpenAIChatResponse);
        var content = parsed?.Choices?.FirstOrDefault()?.Message?.Content ?? string.Empty;
        return new QueueResponse
        {
            Content = content,
            Success = true,
            Model = entry.Id,
            PromptTokens = parsed?.Usage?.PromptTokens ?? 0,
            TokensUsed = parsed?.Usage?.TotalTokens ?? 0,
        };
    }

    private static string Truncate(string s, int max) =>
        s.Length <= max ? s : s[..max] + "…";
}

/// <summary>AOT source-gen 序列化上下文 (模型队列协议 DTO)</summary>
[JsonSerializable(typeof(QueueChatRequest))]
[JsonSerializable(typeof(OpenAIChatResponse))]
[JsonSerializable(typeof(ModelSwitchRecord))]
[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
public partial class ModelQueueJsonContext : JsonSerializerContext
{
}
