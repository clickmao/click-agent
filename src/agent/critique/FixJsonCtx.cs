using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.critique;


[JsonSerializable(typeof(List<FixMemory.FixEntry>))]
internal partial class FixJsonCtx : JsonSerializerContext;
