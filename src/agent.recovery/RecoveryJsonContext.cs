using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.recovery;


/// <summary>检查点 JSON 载荷序列化上下文 (AOT fast-path)</summary>
[JsonSerializable(typeof(ExecutionCheckpoint))]
[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
public partial class RecoveryJsonContext : JsonSerializerContext
{
}
