using System.Text.Json.Serialization;

namespace agent;

/// <summary>
/// LLM 调用链 JSON source-gen 上下文 (AOT: 禁反射序列化)
/// </summary>
[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
[JsonSerializable(typeof(OpenAIChatRequest))]
[JsonSerializable(typeof(OpenAIChatMessage))]
[JsonSerializable(typeof(LLMResponse))]
internal partial class LLMJsonContext : JsonSerializerContext
{
}
