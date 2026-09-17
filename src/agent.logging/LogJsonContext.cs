using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.logging;


[System.Text.Json.Serialization.JsonSerializable(typeof(LogEntry))]
[System.Text.Json.Serialization.JsonSerializable(typeof(FrontendDirective))]
[System.Text.Json.Serialization.JsonSourceGenerationOptions(
    DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull)]
public partial class LogJsonContext : System.Text.Json.Serialization.JsonSerializerContext
{
}
