using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent;

/// <summary>
/// v0.12.0 A2 — 视觉请求 source-gen 上下文 (OpenAIChatRequest 带图路径:
/// messages 序列化为 content parts[], 由 OpenAIChatMessageConverter 承担)。
/// </summary>
[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
[JsonSerializable(typeof(OpenAIChatRequest))]
internal partial class VisionJsonContext : JsonSerializerContext
{
}
