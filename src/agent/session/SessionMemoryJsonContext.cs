using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.session;


/// <summary>AOT source-gen JSON 上下文</summary>
[System.Text.Json.Serialization.JsonSourceGenerationOptions(
    PropertyNameCaseInsensitive = true,
    DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull)]
[JsonSerializable(typeof(SessionMemoryDto))]
internal sealed partial class SessionMemoryJsonContext : JsonSerializerContext;
