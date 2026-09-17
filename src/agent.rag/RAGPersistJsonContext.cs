// v0.11.0 R92: RAG 落盘持久化 DTO + STJ source-gen (用户注意点 2)。
// 手写拼 JSON/手写解析 (R79) 替换为 JsonSourceGenerator — AOT 官方推荐路径, 零反射保持。
// 注: STJ v10 起 JsonSerializerContext 位于 System.Text.Json.Serialization (非 System.Text.Json)。
using System.Text.Json.Serialization;

namespace agent.rag;


/// <summary>STJ source-gen context (零反射, AOT 兼容)</summary>
[JsonSerializable(typeof(RAGPersistDoc))]
internal partial class RAGPersistJsonContext : JsonSerializerContext
{
}
