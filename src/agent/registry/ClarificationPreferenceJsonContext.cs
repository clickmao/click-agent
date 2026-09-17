using System.Text.Json.Serialization;
using agent.intent;
using agent.userinteraction;

namespace agent.registry;


/// <summary>
/// 偏好库 JSON 契约 (source-gen, AOT 安全)。
/// </summary>
[JsonSerializable(typeof(List<ClarificationPreference>))]
[JsonSourceGenerationOptions(WriteIndented = true, PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase)]
internal sealed partial class ClarificationPreferenceJsonContext : System.Text.Json.Serialization.JsonSerializerContext
{
}
