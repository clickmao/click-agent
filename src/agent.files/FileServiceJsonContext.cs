using System.Text.Json.Serialization;

namespace agent.files;

/// <summary>
/// 备份索引序列化上下文 — AOT 零反射（源生成），只覆盖索引行一个类型。
/// </summary>
[JsonSourceGenerationOptions(WriteIndented = false)]
[JsonSerializable(typeof(FileBackupRecord))]
public sealed partial class FileServiceJsonContext : JsonSerializerContext
{
}
