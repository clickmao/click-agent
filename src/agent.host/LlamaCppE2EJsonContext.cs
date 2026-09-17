using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using agent.llamacpp;
using agent.modelqueue;

namespace agent.host;


/// <summary>
/// E2E CLI 的 JSON 上下文（STJ 源生成，AOT 安全）。
/// R411: <c>PropertyNameCaseInsensitive</c> —— 请求文件（<c>--session-json</c>）的键名不得对大小写敏感。
/// 只影响**读取**；输出命名不变（既有消费脚本按精确键名读，不受影响）。
/// </summary>
[JsonSourceGenerationOptions(PropertyNameCaseInsensitive = true)]
[JsonSerializable(typeof(LlamaCppE2EResult))]
[JsonSerializable(typeof(TemplateVerifyResult))]
[JsonSerializable(typeof(LlamaCppSessionRequest))]
[JsonSerializable(typeof(LlamaCppSessionTurnResult))]
[JsonSerializable(typeof(LlamaCppSessionResult))]
[JsonSerializable(typeof(float[]))]
internal sealed partial class LlamaCppE2EJsonContext : JsonSerializerContext;
