using System.Text.Json.Serialization;

namespace agent.modelqueue;


/// <summary>R456: OpenAI tool_call.function (name + arguments 原文)。</summary>
public sealed class OpenAIToolFunction
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("arguments")]
    public string? Arguments { get; set; }
}
