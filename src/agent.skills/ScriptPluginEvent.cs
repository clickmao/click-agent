using System;
using System.Collections.Generic;
using System.Text.Json;

namespace agent.skills;


/// <summary>
/// v0.17.2-b: 单行事件解析产物。字段对应协议: done 带 summary/exit_code(顶层优先, data 兜底) +
/// data.outputs(产物路径数组); error 带 error 消息; heartbeat/progress 带 progress_pct。
/// </summary>
public sealed class ScriptPluginEvent
{
    public ScriptPluginEventType Type { get; set; }
    public long TsUnixMs { get; set; }
    public string Msg { get; set; } = string.Empty;
    public string? Summary { get; set; }
    public int? ExitCode { get; set; }
    public string? Error { get; set; }
    public List<string> Outputs { get; } = new();
    public double? ProgressPct { get; set; }
}
