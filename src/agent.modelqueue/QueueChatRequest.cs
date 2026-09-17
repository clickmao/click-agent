using System.Text.Json.Serialization;

namespace agent.modelqueue;

/// <summary>OpenAI 兼容请求体 (modelqueue 自有 — 与 agent 主程序集解耦)</summary>
public sealed class QueueChatRequest
{
    [JsonPropertyName("model")]
    public string Model { get; set; } = string.Empty;

    [JsonPropertyName("messages")]
    public List<QueueChatMessage> Messages { get; set; } = new();

    // v0.11.0 R19: reasoning 模型思维链计入 max_tokens — 2000 曾被 reasoning 吃满致 content 空 (C03 实测)。
    // 上限只是截断保护, 实际输出长度由 System Prompt 输出纪律约束。
    [JsonPropertyName("max_tokens")]
    public int MaxTokens { get; set; } = 8192;

    [JsonPropertyName("temperature")]
    public double Temperature { get; set; } = 0.7;

    /// <summary>v0.11.0 R22: 推理档位 (glm/deepseek 实测 low 档 reasoning 大降)。null=默认。</summary>
    [JsonPropertyName("reasoning_effort")]
    public string? ReasoningEffort { get; set; }

    /// <summary>R456: 工具声明 JSON (OpenAI 形态)。[JsonIgnore] —— 仅手写 writer 输出 (AOT 安全, 不参与 source-gen)。</summary>
    [JsonIgnore]
    public string? ToolsJson { get; set; }
}
