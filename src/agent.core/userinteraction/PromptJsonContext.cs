using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.userinteraction;

/// <summary>
/// 问询持久化的 source-gen 序列化上下文 (AOT: 禁止反射序列化路径)。
/// 覆盖: 凭据字典 (credentials.json) 与审计条目 (prompt_audit.jsonl)。
/// </summary>
[JsonSourceGenerationOptions(
    PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase,
    DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    WriteIndented = false)]
[JsonSerializable(typeof(Dictionary<string, string>))]
[JsonSerializable(typeof(PromptAuditEntry))]
public partial class PromptJsonContext : JsonSerializerContext
{
}
