using System.Text.Json.Serialization;

namespace agent.modelqueue;


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
