using Microsoft.Extensions.Logging;
using agent.core;
using agent.workspace;
using agent.codegen;
using agent.recovery;
using agent.vectormemory;
using agent.memory;
using agent.templates;
using agent.search;
using agent.subagent;
using agent.session;
using agent.userinteraction;
using agent.context;
using agent.rag;
using agent.tendency;
using agent.tokencompression;
using agent.registry;

using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text;

using agent.intent;

namespace agent;


/// <summary>
/// LLM 响应
/// </summary>
public class LLMResponse
{
    public string Content { get; set; } = string.Empty;
    public bool Success { get; set; } = true;
    public string? Error { get; set; }
    public string Model { get; set; } = "unknown";
    public int TokensUsed { get; set; }
    public double LatencyMs { get; set; }
    
    /// <summary>输入 Token 数</summary>
    public int PromptTokens { get; set; }
    
    /// <summary>输出 Token 数</summary>
    public int CompletionTokens { get; set; }
    
    /// <summary>完成原因（stop, length, content_filter, etc）</summary>
    public string? FinishReason { get; set; }

    /// <summary>v0.21.1: 推理模型思考链 (reasoning_content); 非推理模型为 null。</summary>
    public string? ReasoningContent { get; set; }

    /// <summary>R377: prompt 缓存命中 token (provider 未上报 → null)。</summary>
    public int? CacheHitTokens { get; set; }

    /// <summary>R377: prompt 缓存未命中 token (provider 未上报 → null)。</summary>
    public int? CacheMissTokens { get; set; }

    /// <summary>R414: Content 是否为**面向用户的最终文案**(降级说明) —— Success=false 时链侧也必须透出。
    /// 未标记的失败响应 Content 一律不外泄 (它是内部片段/原始报错)。裁定点: IndustrialAgentV2.UserFacingFailureContent。</summary>
    public bool ContentIsUserFacing { get; set; }

    /// <summary>响应 ID</summary>
    public string? ResponseId { get; set; }
    
    /// <summary>时间戳</summary>
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
}
