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

/// <summary>
/// 完整 Prompt 模型
/// </summary>
public class Prompt
{
    /// <summary>v0.11.0 R21: 推理档位建议 (null=模型默认)。主链按意图启发式设置,
    /// LLM caller 消费 (glm reasoning_effort=low 轻思考: 简单题 reasoning 0 vs 8910ch)。</summary>
    public string? ReasoningEffort { get; set; }

    /// <summary>
    /// 系统 Prompt（包含指令）
    /// </summary>
    public string SystemPrompt { get; set; } = string.Empty;
    
    /// <summary>
    /// 压缩后的上下文
    /// </summary>
    public string ContextPrompt { get; set; } = string.Empty;
    
    /// <summary>
    /// 对话历史
    /// </summary>
    public List<PromptMessage> History { get; set; } = new();
    
    /// <summary>
    /// 当前用户消息
    /// </summary>
    public string UserMessage { get; set; } = string.Empty;
    
    /// <summary>
    /// 完整的组合 Prompt
    /// </summary>
    public string FullPrompt => Compose();
    
    /// <summary>
    /// Token 估算
    /// </summary>
    public int EstimatedTokens { get; set; }
    
    /// <summary>
    /// 组合为完整 Prompt
    /// </summary>
    public string Compose()
    {
        var sb = new System.Text.StringBuilder();
        
        // 1. System Prompt
        if (!string.IsNullOrEmpty(SystemPrompt))
        {
            sb.AppendLine("=== SYSTEM PROMPT ===");
            sb.AppendLine(SystemPrompt);
            sb.AppendLine();
        }
        
        // 2. Context (如果有)
        if (!string.IsNullOrEmpty(ContextPrompt))
        {
            sb.AppendLine("=== CONTEXT ===");
            sb.AppendLine(ContextPrompt);
            sb.AppendLine();
        }
        
        // 3. Conversation History
        if (History.Any())
        {
            sb.AppendLine("=== CONVERSATION HISTORY ===");
            foreach (var msg in History.TakeLast(10)) // 最多10轮
            {
                var role = msg.Role == MessageRole.User ? "User" : "Assistant";
                sb.AppendLine($"[{role}]: {msg.Content}");
            }
            sb.AppendLine();
        }
        
        // 4. Current Message
        sb.AppendLine("=== CURRENT REQUEST ===");
        sb.AppendLine(UserMessage);
        
        return sb.ToString();
    }
}

/// <summary>
/// Prompt 消息
/// </summary>
public class PromptMessage
{
    public MessageRole Role { get; set; }
    public string Content { get; set; } = string.Empty;
    public DateTime Timestamp { get; set; }
}

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
        int maxHistoryTokens = 2000,
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
        
        // 收集历史消息（从后往前取，保持最近的消息）
        // 注意：当前消息不在 history 中（因为还没添加）
        var historyMessages = conversationHistory
            .Where(m => m.Role != MessageRole.System) // 排除系统消息
            .OrderByDescending(m => m.Timestamp)
            .Take(10) // 最近10条
            .Reverse() // 恢复正序
            .ToList();
        
        var historyTokens = 0;
        // v0.11.0 R5: 老消息滚动摘要 — >6 条时把更早的合并为单条摘要, 保最近 6 条完整 (token 治理)
        const int RecentFullCount = 6;
        if (historyMessages.Count > RecentFullCount)
        {
            var older = historyMessages.Take(historyMessages.Count - RecentFullCount).ToList();
            var digest = string.Join(" | ", older.Select(m =>
            {
                var c = m.Content.Replace("\n", " ").Trim();
                return (m.Role == MessageRole.User ? "问:" : "答:") + (c.Length > 40 ? c[..40] + "…" : c);
            }));
            prompt.History.Add(new PromptMessage
            {
                Role = MessageRole.System,
                Content = "【早前对话摘要】" + digest,
                Timestamp = older[0].Timestamp,
            });
            historyTokens += EstimateTokens(digest) + 10;
            historyMessages = historyMessages.Skip(historyMessages.Count - RecentFullCount).ToList();
        }
        foreach (var msg in historyMessages)
        {
            var msgTokens = EstimateTokens(msg.Content);
            if (historyTokens + msgTokens > _maxHistoryTokens)
                break;
            
            prompt.History.Add(new PromptMessage
            {
                Role = msg.Role,
                Content = msg.Content,
                Timestamp = msg.Timestamp
            });
            historyTokens += msgTokens;
        }
        
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

/// <summary>
/// 意图特定的 Prompt 模板
/// </summary>
public class IntentPromptTemplates
{
    private static readonly Dictionary<string, string> _templates = new()
    {
        ["code_generation"] = @"你是一个代码生成专家。请根据用户需求和相关上下文生成高质量代码。

要求：
1. 参考上下文中提供的代码风格和模式
2. 保持与现有代码的一致性
3. 添加必要的注释和文档
4. 确保代码可编译/可运行
5. 遵循 SOLID 原则",

        ["code_modification"] = @"你是一个代码修改专家。请根据用户需求和相关上下文修改代码。

要求：
1. 理解现有代码结构和意图
2. 参考上下文中的相关代码
3. 保持代码风格一致
4. 确保修改不会破坏现有功能
5. 提供修改前后的对比说明",

        ["code_review"] = @"你是一个代码审查专家。请审查代码并提供改进建议。

要求：
1. 参考上下文中的相关代码和历史问题
2. 关注代码质量、安全性、性能
3. 提供具体的改进建议
4. 区分错误(❌)、警告(⚠️)和建议(💡)",

        ["test_generation"] = @"你是一个测试专家。请为代码生成全面的单元测试。

要求：
1. 参考上下文中的源代码
2. 覆盖正常路径和边界情况
3. 使用合适的测试框架(xUnit/NUnit/MSTest)
4. 确保测试可独立运行
5. 提供有意义的断言",

        ["search"] = @"你是一个搜索专家。请结合上下文信息回答用户问题。

要求：
1. 综合网络搜索结果和上下文信息
2. 引用来源并提供链接
3. 提供准确、完整的信息
4. 区分事实和推测",

        ["memory_search"] = @"你是一个记忆搜索专家。请根据记忆上下文回答用户问题。

要求：
1. 基于记忆中的相关历史回答
2. 引用具体的记忆内容
3. 如果记忆不足以回答，明确说明",

        ["file_operation"] = @"你是一个文件操作助手。请帮助用户管理和操作文件。

要求：
1. 列出文件时提供清晰的目录结构
2. 读取文件时提供语法高亮的代码
3. 提供文件操作的确认提示",

        ["git_operation"] = @"你是一个 Git 操作助手。请帮助用户执行 Git 命令。

要求：
1. 解释将要执行的 Git 操作
2. 提供操作结果的清晰说明
3. 警告潜在风险（如强制推送等）",

        ["general"] = @"你是一个智能助手。请结合提供的上下文信息回答用户问题。

要求：
1. 参考上下文中的相关信息
2. 如果上下文不足以回答，明确说明
3. 提供准确、有帮助的回答
4. 保持对话的连贯性"
    };
    
    /// <summary>
    /// 输出纪律 (v0.11.0 R18): 打点实测 C08 reasoning completion 1875 tok 偏冗长;
    /// 统一附加长度约束 — 直接回答优先, 展开细节仅按需。
    /// </summary>
    private const string OutputDiscipline =
        "\n5. 输出纪律：直接回答问题本身，不重复用户问题；无需要时不主动展开背景、对比表或延伸建议；默认简洁，用户追问再展开。" +
        "\n6. 多步任务（调研/报告/对比/计划）：单条回复控制在 500 字以内 — 先给结论与关键依据（要点式），完整长文仅在用户明确要求时生成。";

    /// <summary>
    /// 获取意图对应的 System Prompt
    /// </summary>
    public static string GetSystemPrompt(string intent)
    {
        return _templates.GetValueOrDefault(intent, _templates["general"]) + OutputDiscipline;
    }
}
