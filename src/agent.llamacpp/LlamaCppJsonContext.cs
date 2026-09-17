using System.Text.Json.Serialization;

namespace agent.llamacpp;


[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
[JsonSerializable(typeof(CompletionRequest))]
[JsonSerializable(typeof(CompletionResponse))]
[JsonSerializable(typeof(EmbeddingRequest))]
[JsonSerializable(typeof(EmbeddingResponse))]
[JsonSerializable(typeof(HealthResponse))]
[JsonSerializable(typeof(ApplyTemplateRequest))]
[JsonSerializable(typeof(ApplyTemplateResponse))]
[JsonSerializable(typeof(TokenizeRequest))]
[JsonSerializable(typeof(TokenizeResponse))]
[JsonSerializable(typeof(PropsResponse))]
internal sealed partial class LlamaCppJsonContext : JsonSerializerContext;
