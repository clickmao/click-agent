using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;

namespace agent.skills;


/// <summary>
/// v0.17.2-b: 插件脚本任务载荷 (runner 序列化为 --task-json &lt;file&gt; 交给脚本;
/// 结构化任务描述 + 上下文路径 + 输出目录; ParamsJson 为可选透传 JSON 文本)。
/// </summary>
public sealed class ScriptTaskPayload
{
    [JsonPropertyName("id")] public string Id { get; set; } = string.Empty;
    [JsonPropertyName("goal")] public string Goal { get; set; } = string.Empty;
    [JsonPropertyName("contextPaths")] public List<string> ContextPaths { get; set; } = new();
    [JsonPropertyName("outputDir")] public string OutputDir { get; set; } = string.Empty;
    [JsonPropertyName("paramsJson")] public string ParamsJson { get; set; } = string.Empty;
}
