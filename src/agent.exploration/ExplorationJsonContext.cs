using System.Text.Json.Serialization;

namespace agent.exploration;

/// <summary>
/// v0.13.3 R283 — 探索模块 STJ source-gen (AOT 铁律: 禁反射序列化)。
/// ThinkMemory 持久化 DTO (float[] 由 STJ 原生支持)。
/// </summary>
[JsonSourceGenerationOptions(WriteIndented = false)]
[JsonSerializable(typeof(List<ThinkRecord>))]
internal partial class ExplorationJsonContext : JsonSerializerContext
{
}
