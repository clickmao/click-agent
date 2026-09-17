using agent.core;
using agent.context;

namespace agent.templates;

/// <summary>
/// Prompt 构建器 - 将上下文真正注入到 LLM Prompt
/// 
/// 区别于 PromptHeaderBuilder（用于日志/调试），
/// 这个类用于构建真正发送给 LLM 的完整 Prompt
/// </summary>
public interface IPromptBuilder
{
    /// <summary>
    /// 构建完整 Prompt
    /// </summary>
    Prompt Build(Message userMessage, ContextAssemblyResult context, string systemPrompt);
    
    /// <summary>
    /// 构建带历史对话的 Prompt
    /// </summary>
    Prompt BuildWithHistory(
        Message userMessage, 
        ContextAssemblyResult context, 
        string systemPrompt,
        IEnumerable<Message> conversationHistory);
}
