using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;

public sealed partial class ModelQueueRouter : IModelQueueCaller
{

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

    /// <summary>
    /// R413: 本地生成尝试。成功 → 直接可用的 <see cref="QueueResponse"/>; 失败/空回/记账违规 → null (调用方降级远端)。
    /// 纪律: 取消必须上抛 (绝不把取消当降级); 空内容不得当成功; 记账恒等 (tokens_evaluated == prompt_n + cache_n)
    /// 不成立 ⇒ 结果**不采信** (R411 口径, 防"自算错而自洽")。
    /// </summary>
    private async Task<QueueResponse?> TryLocalAsync(QueuePrompt prompt, TaskKindHint kind, CancellationToken ct)
    {
        var port = _localPort!;
        var cfg = _catalog.LocalChannel;

        var turns = new List<LocalChatTurn>();
        if (!string.IsNullOrEmpty(prompt.SystemPrompt))
            turns.Add(new LocalChatTurn("system", prompt.SystemPrompt));
        if (!string.IsNullOrEmpty(prompt.ContextPrompt))
            turns.Add(new LocalChatTurn("system", prompt.ContextPrompt));
        foreach (var h in prompt.History)
            turns.Add(new LocalChatTurn(h.Role, h.Content));
        turns.Add(new LocalChatTurn("user", prompt.UserMessage));

        var request = new LocalGenerationRequest
        {
            SessionKey = prompt.SessionId,
            TurnIndex = prompt.TurnIndex <= 0 ? 1 : prompt.TurnIndex,
            Turns = turns,
            MaxTokens = cfg.MaxTokens > 0 ? cfg.MaxTokens : 256,
        };

        LocalChannel.RecordAttempt();
        LocalGenerationOutcome outcome;
        try
        {
            outcome = await port.GenerateAsync(request, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            LocalChannel.RecordDegrade($"exception:{ex.GetType().Name}");
            LocalChannelLastBasis = $"local:degraded:exception:{ex.GetType().Name}→remote";
            _logger.LogWarning("ModelQueue: 本地生成异常 ({Kind}) → 降级远端: {Msg}", kind, ex.Message);
            return null;
        }

        if (!outcome.Success)
        {
            LocalChannel.RecordDegrade(outcome.Error ?? "failed");
            LocalChannelLastBasis = $"local:degraded:{outcome.Error ?? "failed"}→remote";
            return null;
        }

        if (string.IsNullOrWhiteSpace(outcome.Content))
        {
            // 空回不是成功 (本地小模型静默空输出的真实失效形态)
            LocalChannel.RecordDegrade("empty_content");
            LocalChannelLastBasis = "local:degraded:empty_content→remote";
            return null;
        }

        if (!outcome.AccountingConsistent)
        {
            var reason = $"tokens_evaluated({outcome.TokensEvaluated}) != prompt_n({outcome.PromptNewTokens}) + cache_n({outcome.CachedTokens})";
            LocalChannel.RecordAccountingViolation(reason);
            LocalChannelLastBasis = "local:degraded:accounting_inconsistent→remote";
            _logger.LogWarning("ModelQueue: 本地记账恒等违规 → 结果不采信, 降级远端: {Reason}", reason);
            return null;
        }

        LocalChannel.RecordSuccess();
        LocalChannelLastBasis = $"local:ok:{port.BackendId}";
        LastSelectionBasis = $"local:{port.BackendId}";
        return new QueueResponse
        {
            Content = outcome.Content,
            Success = true,
            Model = string.IsNullOrEmpty(outcome.Model) ? $"local:{port.BackendId}" : outcome.Model,
            PromptTokens = outcome.TokensEvaluated,
            TokensUsed = outcome.TokensEvaluated + outcome.GeneratedTokens,
            CacheHitTokens = outcome.CachedTokens,
            CacheMissTokens = outcome.PromptNewTokens,
        };
    }
}
