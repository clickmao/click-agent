using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.logging;


[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
[JsonSerializable(typeof(FrontendDirective))]
public partial class ChatboxJsonContext : JsonSerializerContext
{
}
