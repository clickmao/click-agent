using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.registry;


/// <summary>AOT source-gen: 注册表 + 预估共用 (禁反射序列化)</summary>
[JsonSourceGenerationOptions(WriteIndented = true)]
[JsonSerializable(typeof(AgentRegistryFile))]
[JsonSerializable(typeof(ForecastRecord))]
internal partial class RegistryJsonContext : JsonSerializerContext
{
}
