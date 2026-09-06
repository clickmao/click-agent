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
}

public sealed class QueueChatMessage
{
    [JsonPropertyName("role")]
    public string Role { get; set; } = "user";

    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;
}

/// <summary>OpenAI 兼容 chat completions 响应 (C.3.3 — 非流式, source-gen AOT)</summary>
public sealed class OpenAIChatResponse
{
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("choices")]
    public List<OpenAIChatChoice>? Choices { get; set; }

    [JsonPropertyName("usage")]
    public OpenAIChatUsage? Usage { get; set; }
}

public sealed class OpenAIChatChoice
{
    [JsonPropertyName("index")]
    public int Index { get; set; }

    [JsonPropertyName("message")]
    public OpenAIChatResponseMessage? Message { get; set; }

    [JsonPropertyName("finish_reason")]
    public string? FinishReason { get; set; }
}

public sealed class OpenAIChatResponseMessage
{
    [JsonPropertyName("role")]
    public string? Role { get; set; }

    [JsonPropertyName("content")]
    public string? Content { get; set; }
}

public sealed class OpenAIChatUsage
{
    [JsonPropertyName("prompt_tokens")]
    public int PromptTokens { get; set; }

    [JsonPropertyName("completion_tokens")]
    public int CompletionTokens { get; set; }

    [JsonPropertyName("total_tokens")]
    public int TotalTokens { get; set; }
}
