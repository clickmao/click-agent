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

    public async Task<LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
    {
        var qp = new QueuePrompt
        {
            SystemPrompt = prompt.SystemPrompt,
            ContextPrompt = prompt.ContextPrompt,
            UserMessage = prompt.UserMessage,
            EstimatedTokens = prompt.EstimatedTokens,
        };
        foreach (var msg in prompt.History)
            qp.History.Add(new QueueHistoryMessage
            {
                Role = msg.Role == MessageRole.User ? "user" : "assistant",
                Content = msg.Content,
            });
        var r = await _router.CallAsync(qp, TaskKindHint.General, "general", ct);
        return new LLMResponse
        {
            Content = r.Content,
            Success = r.Success,
            Error = r.Error,
            Model = r.Model,
            PromptTokens = r.PromptTokens,
            TokensUsed = r.TokensUsed,
        };
    }
}
