using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;


/// <summary>AOT source-gen 序列化上下文 (模型队列协议 DTO)</summary>
[JsonSerializable(typeof(QueueChatRequest))]
[JsonSerializable(typeof(OpenAIChatResponse))]
[JsonSerializable(typeof(ModelSwitchRecord))]
[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
public partial class ModelQueueJsonContext : JsonSerializerContext
{
}
