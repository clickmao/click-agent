using System.Text.Json.Serialization;

namespace agent.modelqueue;


public sealed class OpenAIChatResponseMessage
{
    [JsonPropertyName("role")]
    public string? Role { get; set; }

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    /// <summary>
    /// v0.21.1: 推理模型思考链 (DeepSeek deepseek-flash / deepseek-reasoner 等返回)。
    /// OpenAI 兼容协议字段; 非推理模型 (deepseek-chat) 不返回 → null, source-gen WhenWritingNull 自动省略。
    /// 内部用例实测 (probes/deepseek-probe): 项目首选模型 deepseek-flash 即推理模型, 此前该字段被整段丢弃。
    /// </summary>
    [JsonPropertyName("reasoning_content")]
    public string? ReasoningContent { get; set; }

    /// <summary>R456 解析面: OpenAI 兼容 tool_calls (source-gen 反序列化, 零反射)。</summary>
    [JsonPropertyName("tool_calls")]
    public List<OpenAIToolCall>? ToolCalls { get; set; }
}
