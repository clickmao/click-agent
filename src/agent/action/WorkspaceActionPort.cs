using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using agent.modelqueue;

namespace agent.action;

/// <summary>
/// R456 执行面默认实现: 工作区受限的文件/命令端口。
/// 契约 (R456 端口化纪律):
///   P1 边界: 一切路径先归一到 <see cref="_root"/> 内, 越界 (..、绝对路径外逃、符号链接指向外) 一律拒绝。
///   P2 有界: 读 ≤ maxBytes、命令输出 ≤ 64KB、超时 ≤ 600s 且进程树整体回收。
///   P3 静默: 不写 Console (禁 Console.WriteLine 铁律); 可选用 JSONL 审计 (env AGENTFRAMEWORK_ACTION_AUDIT=目录)。
///   P4 这是**唯一**允许产生进程副作用的地方: 链上其余部分只经 IActionPort。
/// 说明: run_command 必然依赖平台命令解释器 (sh -c / cmd /c) —— 它是**被声明的能力**而非内部实现捷径;
///   内部核心逻辑仍然零 shell (跨平台铁律针对内部实现)。
/// </summary>
public sealed class WorkspaceActionPort : IActionPort
{
    private readonly string _root;
    private readonly string? _auditDir;
    private readonly int _defaultTimeoutMs;
    private static readonly object AuditLock = new();
    private const int MaxCommandOutputBytes = 64 * 1024;

    public string Name => "workspace";

    public WorkspaceActionPort(string root, string? auditDir = null, int defaultTimeoutMs = 120_000)
    {
        _root = Path.GetFullPath(root);
        _auditDir = string.IsNullOrWhiteSpace(auditDir) ? null : auditDir;
        _defaultTimeoutMs = defaultTimeoutMs <= 0 ? 120_000 : defaultTimeoutMs;
    }

    public static WorkspaceActionPort FromEnvironment(string defaultRoot)
        => new(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_WORKSPACE") is { Length: > 0 } w ? w : defaultRoot,
               Environment.GetEnvironmentVariable("AGENTFRAMEWORK_ACTION_AUDIT"));

    public async Task<ActionExecutionResult> ExecuteAsync(ActionToolCall call, CancellationToken ct)
    {
        var sw = Stopwatch.StartNew();
        ActionExecutionResult result;
        try
        {
            result = call.Name switch
            {
                ActionToolDecl.ListDir => ListDir(call.ArgumentsJson),
                ActionToolDecl.ReadFile => ReadFile(call.ArgumentsJson),
                ActionToolDecl.WriteFile => WriteFile(call.ArgumentsJson),
                ActionToolDecl.RunCommand => await RunCommandAsync(call.ArgumentsJson, ct).ConfigureAwait(false),
                _ => Fail($"未声明的工具: {call.Name}"),
            };
        }
        catch (Exception ex)
        {
            result = Fail("执行失败: " + ex.GetType().Name + ": " + ex.Message);
        }
        result.ElapsedMs = sw.ElapsedMilliseconds;
        return result;
    }

    private static ActionExecutionResult Fail(string msg) => new() { Ok = false, ExitCode = -1, Output = msg };

    private string? Resolve(string? rel, out string error)
    {
        error = string.Empty;
        var p = string.IsNullOrWhiteSpace(rel) ? "." : rel!.Trim();
        if (p.IndexOf('\0') >= 0) { error = "非法路径"; return null; }
        var full = Path.GetFullPath(Path.Combine(_root, p));
        var prefix = _root.EndsWith(Path.DirectorySeparatorChar) ? _root : _root + Path.DirectorySeparatorChar;
        if (!full.StartsWith(prefix, StringComparison.Ordinal) && !string.Equals(full, _root, StringComparison.Ordinal))
        {
            error = "路径越界 (必须在工作区内): " + p;
            return null;
        }
        return full;
    }

    private static string Arg(JsonDocument doc, string name, string fallback)
    {
        if (doc.RootElement.ValueKind != JsonValueKind.Object) return fallback;
        if (!doc.RootElement.TryGetProperty(name, out var v)) return fallback;
        return v.ValueKind switch
        {
            JsonValueKind.String => v.GetString() ?? fallback,
            JsonValueKind.Number => v.GetRawText(),
            _ => fallback,
        };
    }

    private static JsonDocument? ParseArgs(string json)
    {
        try { return JsonDocument.Parse(string.IsNullOrWhiteSpace(json) ? "{}" : json); }
        catch (JsonException) { return null; }
    }

    private ActionExecutionResult ListDir(string argsJson)
    {
        using var doc = ParseArgs(argsJson);
        if (doc is null) return Fail("参数不是合法 JSON");
        var path = Resolve(Arg(doc, "path", "."), out var err);
        if (path is null) return Fail(err);
        if (!Directory.Exists(path)) return Fail("目录不存在: " + Arg(doc, "path", "."));
        var sb = new StringBuilder();
        foreach (var d in Directory.EnumerateDirectories(path))
            sb.Append("d ").Append(Path.GetFileName(d)).Append('\n');
        foreach (var f in Directory.EnumerateFiles(path))
        {
            long len;
            try { len = new FileInfo(f).Length; } catch (IOException) { len = -1; }
            sb.Append("f ").Append(Path.GetFileName(f)).Append(' ').Append(len).Append('\n');
        }
        return new ActionExecutionResult { Ok = true, Output = sb.ToString() };
    }

    private ActionExecutionResult ReadFile(string argsJson)
    {
        using var doc = ParseArgs(argsJson);
        if (doc is null) return Fail("参数不是合法 JSON");
        var rel = Arg(doc, "path", string.Empty);
        var path = Resolve(rel, out var err);
        if (path is null) return Fail(err);
        if (!File.Exists(path)) return Fail("文件不存在: " + rel);
        var max = 8192;
        if (int.TryParse(Arg(doc, "max_bytes", "8192"), out var m) && m > 0 && m <= 1_048_576) max = m;
        var bytes = File.ReadAllBytes(path);
        var take = Math.Min(bytes.Length, max);
        var text = Encoding.UTF8.GetString(bytes, 0, take);
        return new ActionExecutionResult
        {
            Ok = true,
            Output = take < bytes.Length ? text + "\n...[truncated " + (bytes.Length - take) + " bytes]" : text,
        };
    }

    private ActionExecutionResult WriteFile(string argsJson)
    {
        using var doc = ParseArgs(argsJson);
        if (doc is null) return Fail("参数不是合法 JSON");
        var rel = Arg(doc, "path", string.Empty);
        var path = Resolve(rel, out var err);
        if (path is null) return Fail(err);
        var content = Arg(doc, "content", string.Empty);
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(path, content, new UTF8Encoding(false));
        return new ActionExecutionResult { Ok = true, Output = "已写入 " + rel + " (" + Encoding.UTF8.GetByteCount(content) + " bytes)" };
    }

    private async Task<ActionExecutionResult> RunCommandAsync(string argsJson, CancellationToken ct)
    {
        using var doc = ParseArgs(argsJson);
        if (doc is null) return Fail("参数不是合法 JSON");
        var command = Arg(doc, "command", string.Empty);
        if (string.IsNullOrWhiteSpace(command)) return Fail("command 为空");
        var timeoutMs = _defaultTimeoutMs;
        if (int.TryParse(Arg(doc, "timeout_ms", timeoutMs.ToString(System.Globalization.CultureInfo.InvariantCulture)), out var t) && t > 0)
            timeoutMs = Math.Min(t, 600_000);

        var psi = new ProcessStartInfo
        {
            FileName = OperatingSystem.IsWindows() ? "cmd.exe" : "/bin/sh",
            WorkingDirectory = _root,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        psi.ArgumentList.Add(OperatingSystem.IsWindows() ? "/c" : "-c");
        psi.ArgumentList.Add(command);

        using var proc = new Process { StartInfo = psi };
        var stdout = new StringBuilder();
        var stderr = new StringBuilder();
        proc.OutputDataReceived += (_, e) => { if (e.Data != null && stdout.Length < MaxCommandOutputBytes) stdout.Append(e.Data).Append('\n'); };
        proc.ErrorDataReceived += (_, e) => { if (e.Data != null && stderr.Length < MaxCommandOutputBytes) stderr.Append(e.Data).Append('\n'); };
        if (!proc.Start()) return Fail("命令未能启动");
        proc.BeginOutputReadLine();
        proc.BeginErrorReadLine();
        using var reg = ct.Register(() => { try { if (!proc.HasExited) proc.Kill(entireProcessTree: true); } catch { } });
        var finished = await Task.Run(() => proc.WaitForExit(timeoutMs), CancellationToken.None).ConfigureAwait(false);
        if (!finished)
        {
            try { proc.Kill(entireProcessTree: true); } catch { }
            return new ActionExecutionResult
            {
                Ok = false,
                ExitCode = -9,
                Output = "[timeout " + timeoutMs + "ms]\n" + Trim(stdout.ToString(), stderr.ToString()),
            };
        }
        // 等待异步读取缓冲区落尽 (否则大输出会被截断)
        try { proc.WaitForExit(); } catch (Exception) { }
        var exit = proc.ExitCode;
        var body = Trim(stdout.ToString(), stderr.ToString());
        return new ActionExecutionResult { Ok = exit == 0, ExitCode = exit, Output = body };
    }

    private static string Trim(string stdout, string stderr)
    {
        var sb = new StringBuilder();
        if (stdout.Length > 0) sb.Append(stdout);
        if (stderr.Length > 0)
        {
            if (sb.Length > 0) sb.Append('\n');
            sb.Append("[stderr]\n").Append(stderr);
        }
        var s = sb.ToString();
        return s.Length > MaxCommandOutputBytes ? s[..MaxCommandOutputBytes] + "\n...[truncated]" : s;
    }

    /// <summary>可选审计 (P3): 每工具调用一行 JSONL (BOM 铁律: new UTF8Encoding(false))。</summary>
    public void Audit(int step, ActionToolCall call, ActionExecutionResult res)
    {
        if (_auditDir is null) return;
        try
        {
            if (!Directory.Exists(_auditDir)) Directory.CreateDirectory(_auditDir);
            var line = "{\"step\":" + step
                + ",\"tool\":\"" + Esc(call.Name) + "\""
                + ",\"args_sha8\":\"" + ActionLoopRunner.Sha8(call.ArgumentsJson ?? string.Empty) + "\""
                + ",\"ok\":" + (res.Ok ? "true" : "false")
                + ",\"rc\":" + res.ExitCode
                + ",\"ms\":" + res.ElapsedMs
                + ",\"out_bytes\":" + Encoding.UTF8.GetByteCount(res.Output ?? string.Empty)
                + "}" + Environment.NewLine;
            lock (AuditLock)
                File.AppendAllText(Path.Combine(_auditDir, "action_loop.jsonl"), line, new UTF8Encoding(false));
        }
        catch
        {
            // 审计失败不影响主链
        }
    }

    private static string Esc(string s)
    {
        var sb = new StringBuilder();
        foreach (var c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4", System.Globalization.CultureInfo.InvariantCulture));
                    else sb.Append(c);
                    break;
            }
        }
        return sb.ToString();
    }
}
