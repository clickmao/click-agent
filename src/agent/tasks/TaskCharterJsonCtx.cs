using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.tasks;


[JsonSerializable(typeof(TaskCharter))]
internal partial class TaskCharterJsonCtx : JsonSerializerContext;
