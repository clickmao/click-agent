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

/// <summary>v0.17.2-b: 脚本插件执行结果状态。</summary>
public enum ScriptPluginRunStatus
{
    Completed,        // done 事件收到 (权威终态)
    Failed,           // error 事件 / 超时 / 协议违例 (无 done/error)
    RejectedInvalid,  // py_compile 验证拒绝 (未执行)
}

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

/// <summary>
/// v0.17.2-b (用户钦定): 脚本插件服务执行器 — CLI 验证 (py_compile) 通过后交给本服务执行。
/// 子进程 python3 script --task-json &lt;file&gt; --heartbeat-secs N (PYTHONUNBUFFERED 强制流式);
/// stdout 按 JSON Lines 事件流消费 (done/error 权威终态, 退出码兜底); 活性监控: &gt;2×heartbeat
/// 无事件 → 疑似挂起打点 (不杀, 总超时才杀进程树); 进度事件计数打点 + 结束回填 summary/outputs。
/// </summary>
public sealed class ScriptPluginRunner
{
    private readonly string _taskDir;
    private readonly Func<string, string, int, int> _cfg;
    private readonly Action<string, string, string?, string?>? _lessonSink; // pattern, summary, solution, context
    private readonly Func<long> _nowMs;

    public ScriptPluginRunner(
        string? dataRoot = null,
        Func<string, string, int, int>? getConfig = null,
        Action<string, string, string?, string?>? lessonSink = null,
        Func<long>? nowMs = null)
    {
        _cfg = getConfig ?? ((_, _, d) => d);
        _lessonSink = lessonSink;
        _nowMs = nowMs ?? (() => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds());
        _taskDir = dataRoot is null
            ? Path.Combine(Environment.CurrentDirectory, "data", "script-plugin", "tasks")
            : Path.Combine(dataRoot, "script-plugin", "tasks");
    }

    /// <summary>执行入口: 验证门 → task-json 落盘 → 子进程事件流执行 → 结果回填。task 文件用后即删。</summary>
    public async Task<ScriptPluginRunResult> RunPluginScriptAsync(
        string scriptPath, ScriptTaskPayload task, CancellationToken ct = default)
    {
        var fileName = Path.GetFileName(scriptPath);
        var validation = await PythonScriptValidator.ValidateAsync(scriptPath, ct).ConfigureAwait(false);
        if (!validation.Valid)
        {
            _lessonSink?.Invoke($"script-invalid:{fileName}",
                $"py_compile 拒绝: {validation.Detail}",
                "脚本先本地 `python3 -m py_compile` 验证通过再提交插件服务执行", scriptPath);
            agent.config.AgentTelemetry.Emit("script_plugin", "ScriptPluginRunner",
                ("script", fileName), ("result", "rejected_invalid"), ("detail", validation.Detail));
            return new ScriptPluginRunResult
            {
                Status = ScriptPluginRunStatus.RejectedInvalid,
                ScriptPath = scriptPath,
                ValidationDetail = validation.Detail,
            };
        }

        var taskJsonPath = await WriteTaskJsonAsync(task, ct).ConfigureAwait(false);
        try
        {
            return await RunCoreAsync(scriptPath, taskJsonPath, ct).ConfigureAwait(false);
        }
        finally
        {
            try { File.Delete(taskJsonPath); } catch { /* 清理失败不致命 (data/ 目录) */ }
        }
    }

    private async Task<string> WriteTaskJsonAsync(ScriptTaskPayload task, CancellationToken ct)
    {
        Directory.CreateDirectory(_taskDir);
        var path = Path.Combine(_taskDir, Guid.NewGuid().ToString("N") + ".json");
        await File.WriteAllTextAsync(path,
            JsonSerializer.Serialize(task, ScriptPluginJsonCtx.Default.ScriptTaskPayload), ct).ConfigureAwait(false);
        return path;
    }

    private async Task<ScriptPluginRunResult> RunCoreAsync(string scriptPath, string taskJsonPath, CancellationToken ct)
    {
        var fileName = Path.GetFileName(scriptPath);
        var heartbeatSecs = Math.Max(1, _cfg("script_plugin", "heartbeat_secs", 30));
        var timeoutSecs = Math.Max(2, _cfg("script_plugin", "timeout_seconds", 300));
        var hangFactor = Math.Max(2, _cfg("script_plugin", "hang_factor", 2));
        var hangAfterMs = heartbeatSecs * 1000L * hangFactor;

        var python = SkillScriptRunner.FindOnPath("python3") ?? SkillScriptRunner.FindOnPath("python");
        if (python is null)
            return new ScriptPluginRunResult
            {
                Status = ScriptPluginRunStatus.Failed, ScriptPath = scriptPath,
                Error = "python3 解释器不可用 (PATH 无 python3/python)",
            };

        var psi = new ProcessStartInfo
        {
            FileName = python,
            Arguments = $"\"{scriptPath}\" --task-json \"{taskJsonPath}\" --heartbeat-secs {heartbeatSecs.ToString(CultureInfo.InvariantCulture)}",
            WorkingDirectory = Path.GetDirectoryName(Path.GetFullPath(scriptPath)) ?? Environment.CurrentDirectory,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };
        psi.Environment["PYTHONUNBUFFERED"] = "1";        // 强制行级流式 (事件实时可见)
        psi.Environment["AGENTFRAMEWORK_SCRIPT_PLUGIN"] = "1";

        var sw = System.Diagnostics.Stopwatch.StartNew();
        var parser = new ScriptEventStreamParser(_nowMs);
        var hangFired = false;

        using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeoutCts.CancelAfter(TimeSpan.FromSeconds(timeoutSecs));
        using var process = new Process { StartInfo = psi };
        process.Start();

        var stdoutTask = Task.Run(() =>
        {
            string? line;
            while ((line = process.StandardOutput.ReadLine()) is not null)
                parser.FeedLine(line);
        }, CancellationToken.None);

        var stderrTail = string.Empty;
        var stderrTask = Task.Run(() =>
        {
            var sb = new StringBuilder();
            string? line;
            while ((line = process.StandardError.ReadLine()) is not null)
                if (sb.Length < 2000) sb.AppendLine(line);
            stderrTail = sb.ToString();
        }, CancellationToken.None);

        // 活性监控: 疑似挂起只打点一次 (不杀 — 观察; 总超时兜底)
        var hangMonitor = Task.Run(async () =>
        {
            while (!process.HasExited && !parser.TerminalReached)
            {
                if (!hangFired && parser.IsSuspectedHang(_nowMs(), hangAfterMs))
                {
                    hangFired = true;
                    agent.config.AgentTelemetry.Emit("script_plugin_hang", "ScriptPluginRunner",
                        ("script", fileName), ("silent_ms", parser.MsSinceLastEvent(_nowMs())),
                        ("threshold_ms", hangAfterMs));
                }
                await Task.Delay(200, CancellationToken.None).ConfigureAwait(false);
            }
        }, CancellationToken.None);

        try
        {
            await process.WaitForExitAsync(timeoutCts.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            // 内部总超时 → 杀进程树, 返回失败 (不抛 — 调用方可直接渲染)
            SkillScriptRunner.KillTree(process);
            await Task.WhenAll(stdoutTask, stderrTask, hangMonitor).ConfigureAwait(false);
            agent.config.AgentTelemetry.Emit("script_plugin", "ScriptPluginRunner",
                ("script", fileName), ("result", "timeout"), ("timeout_secs", timeoutSecs), ("hang", hangFired));
            return new ScriptPluginRunResult
            {
                Status = ScriptPluginRunStatus.Failed, ScriptPath = scriptPath,
                ProcessExitCode = process.ExitCode,
                DurationMs = sw.ElapsedMilliseconds,
                Error = $"超时 ({timeoutSecs}s), 进程树已终止",
                EventCount = parser.EventLines, HeartbeatCount = parser.HeartbeatCount,
                ProgressCount = parser.ProgressCount,
                NoiseLines = parser.NoiseLines, HangObserved = hangFired,
            };
        }
        finally
        {
            if (ct.IsCancellationRequested && !process.HasExited)
                SkillScriptRunner.KillTree(process); // 外层取消: 不吞异常, 但不留孤儿
        }

        await Task.WhenAll(stdoutTask, stderrTask, hangMonitor).ConfigureAwait(false);

        var exitCode = process.ExitCode;
        var result = new ScriptPluginRunResult
        {
            ScriptPath = scriptPath,
            ProcessExitCode = exitCode,
            DurationMs = sw.ElapsedMilliseconds,
            EventCount = parser.EventLines,
            HeartbeatCount = parser.HeartbeatCount,
            ProgressCount = parser.ProgressCount,
            NoiseLines = parser.NoiseLines,
            HangObserved = hangFired,
        };

        if (parser.TerminalReached && parser.TerminalType == ScriptPluginEventType.Done)
        {
            var ev = parser.TerminalEvent!;
            result.Status = ScriptPluginRunStatus.Completed;
            result.Summary = string.IsNullOrEmpty(ev.Summary) ? ev.Msg : ev.Summary;
            foreach (var o in ev.Outputs) result.Outputs.Add(o);
        }
        else if (parser.TerminalReached)
        {
            var ev = parser.TerminalEvent!;
            result.Status = ScriptPluginRunStatus.Failed;
            result.Error = string.IsNullOrEmpty(ev.Error) ? "脚本 error 事件" : ev.Error;
        }
        else
        {
            // 无终态事件: 退出码仅兜底 — 进程退出 0 但没发 done/error = 协议违例, 同样判失败
            result.Status = ScriptPluginRunStatus.Failed;
            result.Error = exitCode == 0
                ? "协议违例: 进程退出 0 但未发 done/error 事件 (以事件为准, 退出码仅兜底)"
                : $"进程退出码 {exitCode} 且无 done/error 事件";
        }
        if (result.Status == ScriptPluginRunStatus.Failed && string.IsNullOrEmpty(result.Error) is false
            && stderrTail.Trim().Length > 0)
            result.Error = Truncate($"{result.Error} | stderr: {stderrTail.Trim()}", 500);

        agent.config.AgentTelemetry.Emit("script_plugin", "ScriptPluginRunner",
            ("script", fileName), ("result", result.Status.ToString().ToLowerInvariant()),
            ("duration_ms", result.DurationMs), ("events", result.EventCount),
            ("heartbeats", result.HeartbeatCount), ("noise", result.NoiseLines),
            ("outputs", result.Outputs.Count), ("hang", result.HangObserved));
        return result;
    }

    private static string Truncate(string s, int max) => s.Length <= max ? s : s[..max] + "…";
}

/// <summary>STJ source-gen context (AOT: 无反射序列化)。</summary>
[JsonSerializable(typeof(ScriptTaskPayload))]
internal partial class ScriptPluginJsonCtx : JsonSerializerContext;
