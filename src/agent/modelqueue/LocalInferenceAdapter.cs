using agent.core;
using agent.modelqueue;
using agent.templates;

namespace agent.modelqueue;

/// <summary>
/// 本地推理桥 (需求①): agent 侧适配器 — 把 modelqueue 的 ILocalInference 协议桥接到
/// LocalLlamaCaller (ILLMCaller, llama.cpp/gguf 真跑)。Prompt 双向转换在此收敛,
/// LocalLlamaCaller 本身零改动。
/// </summary>
public sealed class LocalInferenceAdapter : ILocalInference
{
    private readonly ILLMCaller _localCaller;

    public LocalInferenceAdapter(ILLMCaller localCaller) => _localCaller = localCaller;

    public bool IsAvailable => _localCaller is agent.llamalocal.LocalLlamaCaller llama &&
                              agent.llamalocal.LocalLlamaCaller.IsModelAvailable(llama.ModelFilePath);

    public string ModelName => _localCaller is agent.llamalocal.LocalLlamaCaller llama
        ? llama.ModelName
        : "local";

    public async Task<QueueResponse> CallAsync(QueuePrompt prompt, CancellationToken ct = default)
    {
        var p = new Prompt
        {
            SystemPrompt = prompt.SystemPrompt,
            ContextPrompt = prompt.ContextPrompt,
            UserMessage = prompt.UserMessage,
            EstimatedTokens = prompt.EstimatedTokens,
        };
        foreach (var msg in prompt.History)
            p.History.Add(new PromptMessage
            {
                Role = msg.Role == "user" ? MessageRole.User : MessageRole.Assistant,
                Content = msg.Content,
            });

        var r = await _localCaller.CallAsync(p, ct);
        return new QueueResponse
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
