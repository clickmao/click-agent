using agent.core;
using agent.modelqueue;
using agent.templates;

namespace agent;

/// <summary>
/// 模型队列适配器 (v7.15 C.3.3): ILLMCaller → ModelQueueRouter。
/// 协议转换: agent Prompt → QueuePrompt; QueueResponse → LLMResponse。
/// DI: ILLMCaller = ModelQueueAdapter (内部持 Router); /model /balance 指令直接用 Router/服务。
/// </summary>
public sealed class ModelQueueAdapter : ILLMCaller, agent.subagent.ILLMCallerForIsolated
{
    private readonly ModelQueueRouter _router;

    public ModelQueueAdapter(ModelQueueRouter router) => _router = router;

    /// <summary>
    /// R379: Prompt → QueuePrompt 协议转换 (自 CallAsync 抽出为单一事实源, 缓存前缀机检直接消费)。
    /// 契约: History 按时间正序**全量**映射 (倒序窗口/截断都会让 provider 缓存前缀失配)。
    /// </summary>
    public static QueuePrompt ToQueuePrompt(Prompt prompt)
    {
        var qp = new QueuePrompt
        {
            SystemPrompt = prompt.SystemPrompt,
            ContextPrompt = prompt.ContextPrompt,
            UserMessage = prompt.UserMessage,
            EstimatedTokens = prompt.EstimatedTokens,
            SessionId = prompt.SessionId,
            TurnIndex = prompt.TurnIndex,
            // v0.11.0 R22: 推理档位透传 (deepseek 实测 low 档 reasoning 24ch vs 90ch)
            ReasoningEffort = prompt.ReasoningEffort,
            // v0.12.0 A2: 图像附件透传 (Router 带图强制云端 + parts[] — 本地 qwen 无视觉, 缺陷 62)
            ImageUrls = prompt.ImageUrls,
        };
        foreach (var msg in prompt.History)
            qp.History.Add(new QueueHistoryMessage
            {
                Role = msg.Role == MessageRole.User ? "user" : "assistant",
                Content = msg.Content,
            });
        return qp;
    }

    public async Task<LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
    {
        var qp = ToQueuePrompt(prompt);
        // R373: 意图透传 (此前硬编码 "general" → 首轮预算策略永远匹配不上, 真机铁证:
        // 代码任务首轮 completion_tokens=8192 被推理吃满 → content 空/半截, 每题 2 次调用)。
        var intent = string.IsNullOrWhiteSpace(prompt.Intent) ? "general" : prompt.Intent!;
        var r = await _router.CallAsync(qp, TaskKindHint.General, intent, ct);
        return new LLMResponse
        {
            Content = r.Content,
            Success = r.Success,
            Error = r.Error,
            Model = r.Model,
            PromptTokens = r.PromptTokens,
            TokensUsed = r.TokensUsed,
            CacheHitTokens = r.CacheHitTokens,
            CacheMissTokens = r.CacheMissTokens,
            ReasoningContent = r.ReasoningContent,
            // R414: "失败但有面向用户的文案"的契约位必须透传 (否则链侧无从区分"可展示文案"与"内部片段")
            ContentIsUserFacing = r.ContentIsUserFacing,
        };
    }
}
