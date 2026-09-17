using agent.core;
using agent.context;

namespace agent.templates;


/// <summary>
/// 完整 Prompt 模型
/// </summary>
public class Prompt
{
    /// <summary>v0.11.0 R21: 推理档位建议 (null=模型默认)。主链按意图启发式设置,
    /// LLM caller 消费 (glm reasoning_effort=low 轻思考: 简单题 reasoning 0 vs 8910ch)。</summary>
    public string? ReasoningEffort { get; set; }

    /// <summary>R373: 任务意图透传 (主链意图分类器的结果, 如 code_generation)。
    /// 消费方 = 模型队列: 决定首轮输出预算 (推理与正文共享 max_tokens → 代码类必须给足)。</summary>
    public string? Intent { get; set; }

    /// <summary>
    /// R494: **隔离通道标记** (结构量, 由调用点显式置位, 非文本判据)。
    /// true = 该 prompt 属隔离执行通道 (微步骤隔离问询 / 一次性隔离子任务): 上下文为空、
    /// system 明示"不引用任何外部会话历史" ⇒ **结构上没有工作区**。
    /// 消费方 = 模型队列声明面: 通道轴开时不下发工作区工具 (默认 false ⇒ 行为与 R490..R493 一致)。
    /// </summary>
    public bool IsolatedChannel { get; set; }

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

    /// <summary>R379: 本次因预算上限被整轮丢弃的历史消息条数 (0 = 完全追加式, KPI 归因用)。</summary>
    public int HistoryTrimmedMessages { get; set; }
    
    /// <summary>
    /// 当前用户消息
    /// </summary>
    public string UserMessage { get; set; } = string.Empty;

    /// <summary>
    /// v0.12.0 A2: 图像附件 (URL 或本地路径 — 本地路径由 LLM caller 转 base64 data URL)。
    /// 非空时 user 消息序列化为多段 content (text + image_url × N)。
    /// </summary>
    public List<string> ImageUrls { get; set; } = new();
    
    /// <summary>
    /// 完整的组合 Prompt
    /// </summary>
    public string FullPrompt => Compose();
    
    /// <summary>
    /// Token 估算
    /// </summary>
    public int EstimatedTokens { get; set; }

    /// <summary>R379: 会话标识 (缓存前缀 KPI 归属; 空 = 一次性请求)。</summary>
    public string? SessionId { get; set; }

    /// <summary>R379: 本会话内第几轮 (1 起; 红线判据 = 第 2 轮起命中率 ≥90%)。</summary>
    public int TurnIndex { get; set; }
    
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
