using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;


/// <summary>队列调用响应 (协议自洽)</summary>
public sealed class QueueResponse
{
    /// <summary>R478: 逐调用因果 id —— llm_call.request_id ↔ loop_turn.request_id 同一值 join,
    /// 取代「时间窗归属」(R477 P4: 5 次调用落在 turn 窗口外 ⇒ 归属不可因果)。</summary>
    public string RequestId { get; set; } = "";

    public string Content { get; set; } = string.Empty;
    public bool Success { get; set; } = true;
    public string? Error { get; set; }
    public string Model { get; set; } = "unknown";
    public int PromptTokens { get; set; }
    public int TokensUsed { get; set; }

    /// <summary>v0.21.1: 推理模型思考链 (reasoning_content); 非推理模型为 null。</summary>
    public string? ReasoningContent { get; set; }

    /// <summary>v0.10.0: 输出 token 数 (TokensUsed = prompt + completion)</summary>
    public int CompletionTokens => Math.Max(0, TokensUsed - PromptTokens);

    /// <summary>R377: prompt 缓存命中 token (provider 未上报 → null, 不得当 0)。</summary>
    public int? CacheHitTokens { get; set; }

    /// <summary>R377: prompt 缓存未命中 token (provider 未上报 → null)。</summary>
    public int? CacheMissTokens { get; set; }

    /// <summary>R456 解析面: 模型请求的工具调用 (空 = 纯文本回复, 与旧版行为一致)。</summary>
    public List<ActionToolCall>? ToolCalls { get; set; }

    /// <summary>R456: 上游 finish_reason (tool_calls/stop/length — 归因用)。</summary>
    public string? FinishReason { get; set; }

    /// <summary>R414: 本响应的 Content 是否为**面向用户的最终文案**(降级说明等) —— Success=false 时也必须在链上透出。
    /// false = Content 只是内部片段/原始报错, 链侧不得当作用户可见正文(避免错误正文/内部信息外泄)。</summary>
    public bool ContentIsUserFacing { get; set; }
}
