using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.critique;


[JsonSerializable(typeof(List<GuardrailMemory.GuardrailEntry>))]
internal partial class GuardrailJsonCtx : JsonSerializerContext;
