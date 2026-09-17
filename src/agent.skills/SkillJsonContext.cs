using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.skills;


[JsonSerializable(typeof(SkillResult))]
[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
public partial class SkillJsonContext : JsonSerializerContext
{
}
