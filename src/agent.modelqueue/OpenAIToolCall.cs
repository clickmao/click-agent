using System.Text.Json.Serialization;

namespace agent.modelqueue;


/// <summary>R456: OpenAI tool_call 条目。</summary>
public sealed class OpenAIToolCall
{
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("function")]
    public OpenAIToolFunction? Function { get; set; }
}
