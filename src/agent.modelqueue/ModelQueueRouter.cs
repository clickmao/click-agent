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

    /// <summary>需求①: 本地推理桥 (宿主注入; null = 无本地模型, 通道自动不可用)</summary>
    private readonly ILocalInference? _localInference;
    private readonly TokenUsageService? _tokenUsage;

    /// <summary>需求1: 官方 key 仓库 (CLI --official-key / /official-key 注入; 永不落盘)</summary>
    public OfficialKeyStore OfficialKeys { get; } = new();

    /// <summary>需求1: 三通道调度 (本地&gt;官方&gt;远端; 并发数托管)</summary>
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
        ILocalInference? localInference = null,
        TokenUsageService? tokenUsage = null)
    {
        _catalog = catalog;
        _policy = new ModelSelectionPolicy();
        _httpClientFactory = httpClientFactory;
        _logger = logger;
        _localInference = localInference;
        _tokenUsage = tokenUsage;
        Scheduler = scheduler ?? new ChannelScheduler();
        // 本地通道可用性 = 桥接的本地模型就绪 (ChannelScheduler 已默认 Local 可用, 这里按事实修正)
        Scheduler.SetAvailable(ModelChannel.Local, localInference?.IsAvailable ?? false);
        // 官方通道可用性 = key 已注入 (注入/撤销时由指令处理刷新)
        Scheduler.SetAvailable(ModelChannel.Official, OfficialKeys.IsAvailable());
    }

    /// <summary>官方 key 注入入口 (CLI 启动参数/指令 — 同步刷新官方通道可用性)</summary>
    public void SetOfficialKey(string? key)
    {
        OfficialKeys.Set(key);
        Scheduler.SetAvailable(ModelChannel.Official, OfficialKeys.IsAvailable());
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
        // 需求① 本地通道真跑: 无手动覆盖/粘性时, 本地优先 (并发余量内) — LocalInferenceAdapter 实跑子任务
        bool useLocal = false;
        lock (_lock)
        {
            if (_manualOverride is null && _activeModelId is null &&
                _localInference is not null && _localInference.IsAvailable)
            {
                var localChannel = Scheduler.AcquireChannel();
                if (localChannel == ModelChannel.Local)
                {
                    useLocal = true;
                    LastSelectionBasis = $"channel:local:{_localInference.ModelName}";
                }
                else if (localChannel is not null)
                    Scheduler.ReleaseChannel(localChannel.Value); // 首选非 Local (本地满) → 按其通道语义继续
            }
        }
        if (useLocal)
        {
            try
            {
                var localResp = await _localInference!.CallAsync(prompt, ct).ConfigureAwait(false);
                Scheduler.ReleaseChannel(ModelChannel.Local);
                return localResp;
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                Scheduler.ReleaseChannel(ModelChannel.Local);
                return new QueueResponse
                {
                    Success = false,
                    Error = $"本地模型调用失败: {ex.Message}",
                    Model = _localInference!.ModelName,
                };
            }
        }

        // 需求1 混合调度: 手动/粘性优先 → 通道优先级 (官方 key 在 → 官方可作候选; 远端目录在 → 远端)
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

        try
        {
            var resp = await CallEntryAsync(entry, prompt, ct);
            lock (_lock) _consecutiveFailures = 0;
            // v0.10.0: 用量本地累计
            _tokenUsage?.RecordUsage(resp.Model, entry.Provider, resp.PromptTokens, resp.CompletionTokens);
            agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                ("model", entry.Id), ("provider", entry.Provider),
                ("prompt_tokens", resp.PromptTokens), ("completion_tokens", resp.CompletionTokens),
                ("total_tokens", resp.TokensUsed), ("success", true),
                // v0.11.0 R19: 内容长度诊断 (C03 曾现 completion 2000 tok 但回复渲染空 — 定位内容丢在链路哪段)
                ("content_len", resp.Content?.Length ?? 0));
            // 阈值再同步 (fire-and-forget, 不阻塞主链)
            if (_tokenUsage is not null && _tokenUsage.NeedsResync(entry.Provider))
                _ = _tokenUsage.TryResyncAsync(entry.Provider, CancellationToken.None);
            return resp;
        }
        catch (HttpRequestException ex)
        {
            agent.config.AgentTelemetry.Emit("llm_call", "ModelQueueRouter",
                ("model", entry.Id), ("provider", entry.Provider), ("success", false), ("error_kind", "http"), ("error", ex.Message));
            return await OnTransientFailureAsync(entry, prompt, kind, intent, ct, $"网络错误: {ex.Message}").ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            // HttpClient 超时 (非用户取消) = 瞬态
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
            _logger.LogWarning("ModelQueue: {Model} 瞬态失败 ({Why}) — 请求内重试 {Attempt}/2", entry.Id, why, attempt);
            agent.config.AgentTelemetry.Emit("llm_retry", "ModelQueueRouter",
                ("model", entry.Id), ("attempt", attempt), ("why", why));
            try
            {
                var retried = await CallEntryAsync(entry, prompt, ct).ConfigureAwait(false);
                if (retried.Success)
                {
                    lock (_lock) _consecutiveFailures = 0;
                    LastSelectionBasis = $"retry_ok:{entry.Id} (attempt {attempt + 1})";
                    _tokenUsage?.RecordUsage(retried.Model, entry.Provider, retried.PromptTokens, retried.CompletionTokens);
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

        // 重试耗尽 → 切备选模型 (同目录下一个不同 id、key 可用的模型)
        ModelCatalogEntry? backup;
        lock (_lock)
        {
            _consecutiveFailures++;
            backup = _catalog.Models.FirstOrDefault(m =>
                !string.Equals(m.Id, entry.Id, StringComparison.OrdinalIgnoreCase) &&
                (m.ApiKeyEnv is null ||
                 !string.IsNullOrEmpty(Environment.GetEnvironmentVariable(m.ApiKeyEnv))));
        }
        if (backup is not null)
        {
            _logger.LogWarning("ModelQueue: {From} 重试耗尽 → 切备 {To}", entry.Id, backup.Id);
            agent.config.AgentTelemetry.Emit("llm_failover", "ModelQueueRouter",
                ("from", entry.Id), ("to", backup.Id), ("why", why));
            try
            {
                var backupResp = await CallEntryAsync(backup, prompt, ct).ConfigureAwait(false);
                if (backupResp.Success)
                {
                    lock (_lock)
                    {
                        Switches.Add(new ModelSwitchRecord
                            { From = entry.Id, To = backup.Id, Reason = "transient_failover" });
                        _activeModelId = backup.Id;
                        _manualOverride = null;
                        _consecutiveFailures = 0;
                        LastSelectionBasis = $"failover:{backup.Id} (原 {entry.Id} 瞬态失败)";
                    }
                    _tokenUsage?.RecordUsage(backupResp.Model, backup.Provider, backupResp.PromptTokens, backupResp.CompletionTokens);
                    return backupResp;
                }
                return backupResp; // 备选也软失败, 如实返回
            }
            catch (Exception ex3) when (ex3 is HttpRequestException
                || (ex3 is OperationCanceledException oce && !ct.IsCancellationRequested))
            {
                return new QueueResponse
                {
                    Success = false,
                    Error = $"主模型 {entry.Id} 与备选 {backup.Id} 均失败: {ex3.Message}",
                    Model = backup.Id,
                };
            }
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
        // 本地通道可用 → 本地承接 (本地模型无余额限制)
        if (_localInference is not null && _localInference.IsAvailable)
            return null; // 本地走 CallAsync 本地分支, 此处不重复
        if (_tokenUsage is null) return null;
        var candidates = _catalog.Models
            .Where(m => !string.Equals(m.Id, current.Id, StringComparison.OrdinalIgnoreCase))
            .Select(m => (Model: m, Est: _tokenUsage.EstimateBalance(m.Provider, estimatedTokens)))
            .Where(t => t.Est.Sufficient)
            .OrderByDescending(t => t.Model.ReasoningScore + t.Model.CodingScore)
            .ToList();
        return candidates.Count == 0 ? null : candidates[0].Model;
    }

    /// <summary>
    /// 需求1 通道优先级选模 (本地由宿主 LocalLlamaCaller 在 adapter 层直跑, 不占远端并发;
    /// 此处处理官方/远端): 官方 key 在 → 官方通道 RankCandidates 选优; 否则远端目录选优。
    /// 通道满 (AcquireChannel=null) → 不阻塞主链, 退回目录首模型由其自身失败语义兜底。
    /// </summary>
    private ModelCatalogEntry? SelectByChannelPriority(TaskKindHint kind, string intent, int estimatedTokens)
    {
        if (OfficialKeys.IsAvailable())
        {
            var channel = Scheduler.AcquireChannel();
            if (channel is ModelChannel.Official or null)
            {
                if (channel is not null)
                    Scheduler.ReleaseChannel(channel.Value);
                var ranked = Scheduler.RankCandidates(OfficialModels.Models, kind, estimatedTokens);
                if (ranked.Count > 0)
                {
                    LastSelectionBasis = $"channel:official:{ranked[0].Model.Id}";
                    return ranked[0].Model;
                }
            }
            else
            {
                Scheduler.ReleaseChannel(channel.Value);
            }
        }
        var remoteRanked = Scheduler.RankCandidates(_catalog.Models, kind, estimatedTokens);
        if (remoteRanked.Count == 0)
            return null;
        LastSelectionBasis = $"channel:remote:{remoteRanked[0].Model.Id}";
        return remoteRanked[0].Model;
    }

    /// <summary>按目录条目真实调用 OpenAI 兼容 chat completions (endpoint/keyEnv 来自目录)</summary>
    private async Task<QueueResponse> CallEntryAsync(ModelCatalogEntry entry, QueuePrompt prompt, CancellationToken ct)
    {
        // official 通道 key 只从内存仓库取 (永不落盘); 其余通道从环境变量
        var apiKey = entry.Provider == "official"
            ? OfficialKeys.Get()
            : Environment.GetEnvironmentVariable(entry.ApiKeyEnv);
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
        messages.Add(new QueueChatMessage { Role = "user", Content = prompt.UserMessage });

        var request = new QueueChatRequest { Model = entry.Id, Messages = messages, ReasoningEffort = prompt.ReasoningEffort };
        using var http = new HttpRequestMessage(HttpMethod.Post, entry.Endpoint)
        {
            Content = new StringContent(
                JsonSerializer.Serialize(request, ModelQueueJsonContext.Default.QueueChatRequest),
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
