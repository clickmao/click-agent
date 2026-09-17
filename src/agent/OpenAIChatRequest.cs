using Microsoft.Extensions.Logging;
using agent.core;
using agent.workspace;
using agent.codegen;
using agent.recovery;
using agent.vectormemory;
using agent.memory;
using agent.templates;
using agent.search;
using agent.session;
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
/// OpenAI chat completion 请求 DTO (AOT: source-gen 序列化, 禁匿名类型反射)
/// </summary>
public sealed class OpenAIChatRequest
{
    [JsonPropertyName("model")]
    public string Model { get; set; } = string.Empty;

    [JsonPropertyName("messages")]
    public List<OpenAIChatMessage> Messages { get; set; } = new();

    [JsonPropertyName("max_tokens")]
    public int MaxTokens { get; set; } = 2000;

    [JsonPropertyName("temperature")]
    public double Temperature { get; set; } = 0.7;

    /// <summary>v0.11.0 R21: glm 推理档位 (low=轻思考)。null=模型默认 (复杂任务保留深推理)。
    /// 实测: 简单题 compl 49tok vs 默认 8910ch reasoning; 复杂题 low 档 wall -55%。
    /// null 时 JSON 忽略 (LLMJsonContext 全局 WhenWritingNull)。</summary>
    [JsonPropertyName("reasoning_effort")]
    public string? ReasoningEffort { get; set; }
}
