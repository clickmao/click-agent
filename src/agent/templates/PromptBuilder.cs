using agent.core;
using agent.context;

namespace agent.templates;


/// <summary>
/// Prompt 构建器实现
/// </summary>
public class PromptBuilder : IPromptBuilder
{
    private readonly int _maxContextTokens;
    private readonly int _maxHistoryTokens;
    private readonly bool _includeMetadata;
    
    public PromptBuilder(
        int maxContextTokens = 4000,
        // R379 (用户钦定): 2000 → 1_000_000。历史预算是命中率的分母治理阀: 预算越小越常触发整轮丢弃,
        // 每次丢弃都让该轮命中率塌到接近 0 (前缀断裂), 与"第 2 轮起 ≥90%、目标 98~99%"直接冲突。
        // 1M 实为"不触发丢弃"的安全阀 (自检/真机同口径), 真正的前缀治理靠追加式回放而非截断。
        int maxHistoryTokens = 1_000_000,
        bool includeMetadata = false)
    {
        _maxContextTokens = maxContextTokens;
        _maxHistoryTokens = maxHistoryTokens;
        _includeMetadata = includeMetadata;
    }
    
    /// <summary>
    /// 构建 Prompt
    /// </summary>
    public Prompt Build(Message userMessage, ContextAssemblyResult context, string systemPrompt)
    {
        // ✅ 使用 ContextAssembler 生成的 PromptHeader
        // 不再重复构建，只复用已有的结果
        var contextPrompt = context.PromptHeader;
        
        var prompt = new Prompt
        {
            SystemPrompt = systemPrompt,
            ContextPrompt = contextPrompt,
            UserMessage = userMessage.Content,
            EstimatedTokens = 
                EstimateTokens(systemPrompt) + 
                EstimateTokens(contextPrompt) + 
                EstimateTokens(userMessage.Content)
        };
        
        return prompt;
    }
    
    /// <summary>
    /// 构建带历史的 Prompt
    /// </summary>
    public Prompt BuildWithHistory(
        Message userMessage,
        ContextAssemblyResult context,
        string systemPrompt,
        IEnumerable<Message> conversationHistory)
    {
        var prompt = Build(userMessage, context, systemPrompt);

        // v0.12.0 A2: 图像附件透传 (CLI -img / Message.ImageAttachments) → LLM caller 多段 content
        prompt.ImageUrls = userMessage.ImageAttachments;

        // ── R379 缓存前缀稳定化 (用户钦定 KPI 红线) ──
        // 历史必须"追加式全量回放": provider 的缓存前缀单元只在"请求从第 0 个 token 起完整匹配"时命中。
        // 旧实现有三处破坏前缀, 已全部移除:
        //   ① 倒序 Take(10) 窗口滑动 → 会话变长时头部消息被丢, 前缀从丢弃点断裂;
        //   ② >6 条滚动摘要重写 → 摘要内容随旧消息滚动变化, 且把已发送字节改写成了别的字节;
        //   ③ 2000 token 预算 break → 按 token 边界截断消息序列。
        // 现策略: 正序全量保留; 仅当总预算超上限时, 从"最旧的一整轮"(user+assistant 对) 整体丢弃,
        // 且一次丢到 60% 预算 (摊薄触发频率), 丢弃条数打进 HistoryTrimmedMessages 供 KPI 归因。
        var historyMessages = conversationHistory
            .Where(m => m.Role != MessageRole.System)
            .OrderBy(m => m.Timestamp)
            .ToList();

        var historyTokens = 0;
        var trimmed = 0;
        var allTokens = historyMessages.Sum(m => EstimateTokens(m.Content));
        if (allTokens > _maxHistoryTokens && _maxHistoryTokens > 0)
        {
            var target = (int)(_maxHistoryTokens * 0.6);
            var budget = allTokens;
            var start = 0;
            while (start < historyMessages.Count && budget > target)
            {
                budget -= EstimateTokens(historyMessages[start].Content);
                start++;
                while (start < historyMessages.Count && historyMessages[start].Role != MessageRole.User)
                    start++; // 对齐整轮边界: 丢到下一个 user 消息之前
            }
            trimmed = start;
            historyMessages = historyMessages.Skip(start).ToList();
        }
        foreach (var msg in historyMessages)
        {
            prompt.History.Add(new PromptMessage
            {
                Role = msg.Role,
                Content = msg.Content,
                Timestamp = msg.Timestamp
            });
            historyTokens += EstimateTokens(msg.Content);
        }
        prompt.HistoryTrimmedMessages = trimmed;
        
        // 重新计算总 Token
        prompt.EstimatedTokens += historyTokens;
        
        return prompt;
    }
    
/// <summary>
    /// 估算 Token 数
    /// </summary>
    private int EstimateTokens(string text)
    {
        if (string.IsNullOrEmpty(text)) return 0;
        
        // 简化的 Token 估算
        var chineseChars = text.Count(c => c >= 0x4E00 && c <= 0x9FFF);
        var englishWords = text.Split(' ', StringSplitOptions.RemoveEmptyEntries).Length;
        
        return (int)(chineseChars * 1.5 + englishWords * 1.3);
    }
}
