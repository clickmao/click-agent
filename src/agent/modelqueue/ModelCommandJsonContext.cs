using System.Text.Json.Serialization;

namespace agent;


/// <summary>模型队列载荷序列化上下文 (AOT: 无反射)</summary>
[System.Text.Json.Serialization.JsonSerializable(typeof(ModelCommandPayload))]
[System.Text.Json.Serialization.JsonSerializable(typeof(ModelListItem))]
[System.Text.Json.Serialization.JsonSerializable(typeof(TokenStatsPayload))]
[System.Text.Json.Serialization.JsonSerializable(typeof(BalanceEntryPayload))]
[System.Text.Json.Serialization.JsonSerializable(typeof(ForecastPayload))]
[System.Text.Json.Serialization.JsonSerializable(typeof(RagInfoPayload))]
[System.Text.Json.Serialization.JsonSerializable(typeof(RagSwitchPayload))]
[System.Text.Json.Serialization.JsonSourceGenerationOptions(
    DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull)]
public partial class ModelCommandJsonContext : System.Text.Json.Serialization.JsonSerializerContext
{
}
