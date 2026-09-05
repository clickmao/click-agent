using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.search;

/// <summary>
/// 搜索插件协议模型的 source-gen 序列化上下文。
/// Native AOT 硬性要求: 所有 JSON 走 source generator, 禁用反射序列化路径。
/// </summary>
[JsonSourceGenerationOptions(
    PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase,
    DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
[JsonSerializable(typeof(BochaRequest))]
[JsonSerializable(typeof(BochaResponse))]
[JsonSerializable(typeof(SearXngResponse))]
[JsonSerializable(typeof(ProviderSlotState))]
internal partial class SearchJsonContext : JsonSerializerContext
{
}
