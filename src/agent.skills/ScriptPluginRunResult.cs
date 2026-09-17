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


/// <summary>v0.17.2-b: 脚本插件执行结果 (done 回填 summary/outputs; 事件计数; 挂起观测)。</summary>
public sealed class ScriptPluginRunResult
{
    public ScriptPluginRunStatus Status { get; set; }
    public string ScriptPath { get; set; } = string.Empty;
    public int ProcessExitCode { get; set; }
    public long DurationMs { get; set; }
    public string Summary { get; set; } = string.Empty;
    public string? Error { get; set; }
    public List<string> Outputs { get; } = new();
    public int EventCount { get; set; }
    public int HeartbeatCount { get; set; }
    public int ProgressCount { get; set; }
    public int NoiseLines { get; set; }
    public bool HangObserved { get; set; }
    public string? ValidationDetail { get; set; }

    public string Render()
    {
        var name = Path.GetFileName(ScriptPath);
        return Status switch
        {
            ScriptPluginRunStatus.Completed =>
                $"✅ [{name}] 完成 ({DurationMs}ms, 事件 {EventCount}, 心跳 {HeartbeatCount}): {Summary}"
                + (Outputs.Count > 0 ? $"\n  产物: {string.Join(", ", Outputs)}" : string.Empty),
            ScriptPluginRunStatus.RejectedInvalid =>
                $"⛔ [{name}] py_compile 验证拒绝, 未执行: {ValidationDetail}",
            _ => $"❌ [{name}] 失败 ({DurationMs}ms): {Error}",
        };
    }
}
