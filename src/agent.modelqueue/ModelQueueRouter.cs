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
        ChannelScheduler? scheduler = null)
    {
        _catalog = catalog;
        _policy = new ModelSelectionPolicy();
        _httpClientFactory = httpClientFactory;
        _logger = logger;
        Scheduler = scheduler ?? new ChannelScheduler();
        // 官方通道可用性 = key 已注入 (注入/撤销时由指令处理刷新)
        Scheduler.SetAvailable(ModelChannel.Official, OfficialKeys.IsAvailable());
    }

    /// <summary>官方 key 注入入口 (CLI 启动参数/指令 — 同步刷新官方通道可用性)</summary>
    public void SetOfficialKey(string? key)
    {
        OfficialKeys.Set(key);
        Scheduler.SetAvailable(ModelChannel.Official, OfficialKeys.IsAvailable());
    }

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

        try
        {
            var resp = await CallEntryAsync(entry, prompt, ct);
            lock (_lock) _consecutiveFailures = 0;
            return resp;
        }
        catch (HttpRequestException ex)
        {
            return OnTransientFailure(entry, prompt, kind, intent, ct, $"网络错误: {ex.Message}");
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            // HttpClient 超时 (非用户取消) = 瞬态
            return OnTransientFailure(entry, prompt, kind, intent, ct, "请求超时");
        }
        catch (OperationCanceledException)
        {
            // 用户取消永不触发模型切换 (C.4 验收)
            throw;
        }
    }

    private QueueResponse OnTransientFailure(ModelCatalogEntry entry, QueuePrompt prompt, TaskKindHint kind, string intent, CancellationToken ct, string why)
    {
        lock (_lock)
        {
            _consecutiveFailures++;
            if (_consecutiveFailures < MaxConsecutiveFailures)
            {
                LastSelectionBasis = $"primary:{entry.Id} (失败 {_consecutiveFailures}/{MaxConsecutiveFailures})";
                return new QueueResponse
                {
                    Success = false,
                    Error = $"模型 {entry.Id} 调用失败 ({_consecutiveFailures}/{MaxConsecutiveFailures}): {why}",
                    Model = entry.Id,
                };
            }

            // 连续失败达上限 → 切备 (同目录中下一个不同 id 的模型)
            var backup = _catalog.Models.FirstOrDefault(m =>
                !string.Equals(m.Id, entry.Id, StringComparison.OrdinalIgnoreCase));
            if (backup is null)
            {
                LastSelectionBasis = $"primary:{entry.Id} (无备选)";
                return new QueueResponse
                {
                    Success = false,
                    Error = $"模型 {entry.Id} 连续失败 {MaxConsecutiveFailures} 次且目录无备选: {why}",
                    Model = entry.Id,
                };
            }
            Switches.Add(new ModelSwitchRecord
                { From = entry.Id, To = backup.Id, Reason = "consecutive_failures" });
            _activeModelId = backup.Id;
            _manualOverride = null; // 失败切换后回到自动粘性
            _consecutiveFailures = 0;
            LastSelectionBasis = $"failover:{backup.Id} (原 {entry.Id} 连续 {MaxConsecutiveFailures} 败)";
            _logger.LogWarning("ModelQueue: {From} 连续失败 → 切换到 {To}", entry.Id, backup.Id);
        }

        // 备模型立即接手本次调用 (不再内嵌重试 — 计划级重试由 TaskPlanExecutor 负责)
        try
        {
            var backupEntry = _catalog.Find(_activeModelId)!;
            return CallEntryAsync(backupEntry, prompt, ct).GetAwaiter().GetResult();
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException)
        {
            return new QueueResponse
            {
                Success = false,
                Error = $"备模型也失败: {ex.Message}",
                Model = _activeModelId,
            };
        }
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

        var request = new QueueChatRequest { Model = entry.Id, Messages = messages };
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
