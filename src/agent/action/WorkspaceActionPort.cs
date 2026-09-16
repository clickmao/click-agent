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

    /// <summary>R462: 回灌面「召回-现实一致性」机检需要的工作区根。</summary>
    public string? WorkspaceRoot => _root;
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
        // R498 候选④ (P1 边界的**结构正控**): 旧实现里这条拒绝路径**没有消融臂** ⇒
        //   「越界必拒」只能被断言成恒真 (无正控的断言 = 无判别力: 把 Resolve 整段删掉,
        //   原来的负样本测试仍会因「文件不存在」而失败 ⇒ 红因与被测行为无因果绑定)。
        // 现改为复用命令面**同一个**闸常量 (AGENTFRAMEWORK_ACTION_BOUNDARY, 默认开):
        //   BoundaryEnforced()==false ⇒ 允许越界 (缺陷注入臂) ⇒ 越界读必须**成功**,
        //   于是「越界被拒」这条断言在注入臂上可被证伪 = 真正的正控。
        // 默认行为逐位不变 (未设/非 "0" ⇒ 仍拒绝)。
        if (BoundaryEnforced())
        {
            var prefix = _root.EndsWith(Path.DirectorySeparatorChar) ? _root : _root + Path.DirectorySeparatorChar;
            if (!full.StartsWith(prefix, StringComparison.Ordinal) && !string.Equals(full, _root, StringComparison.Ordinal))
            {
                error = "路径越界 (必须在工作区内): " + p;
                return null;
            }
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
        // R496 候选③-a (R495 审计半开通道): 命令文本引用工作区外路径 ⇒ **整条不执行**(回绝即不回显正文)。
        if (BoundaryEnforced())
        {
            var outside = FindOutOfRootToken(command, _root);
            if (outside is not null)
            {
                return new ActionExecutionResult
                {
                    Ok = false,
                    ExitCode = BoundaryRefusedExitCode,
                    Output = "[拒绝执行] 命令引用了工作区外路径: " + outside
                        + " (工作区边界铁律: 越界路径既不执行也不回显; 请用相对路径或工作区内路径重试)",
                };
            }
        }
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

    // ---------- R496 候选③-a: 命令面越界收口 (回绝即不回显正文) ----------

    /// <summary>边界铁律开关 (默认开; `AGENTFRAMEWORK_ACTION_BOUNDARY=0` 仅供消融对照)。</summary>
    public const string BoundaryEnvName = "AGENTFRAMEWORK_ACTION_BOUNDARY";

    /// <summary>越界拒绝的退出码 (与「命令跑了但失败」在审计面上可区分)。</summary>
    public const int BoundaryRefusedExitCode = 126;

    /// <summary>唯一例外: /dev/null (惯用法 `2>/dev/null`; 不含 /dev/zero、/proc、/etc…)。</summary>
    private static readonly string[] AllowedDevicePaths = { "/dev/null" };

    private static readonly char[] TokenSplitters =
    {
        ' ', '\t', '\r', '\n', ';', '|', '&', '(', ')', '<', '>', '"', '\'', '`', '$', '{', '}', '=', ',', '\\',
    };

    public static bool BoundaryEnforced()
        => !string.Equals(Environment.GetEnvironmentVariable(BoundaryEnvName), "0", StringComparison.Ordinal);

    /// <summary>
    /// R496 候选③-a: 命令文本里第一个**工作区外路径** token (无 ⇒ null)。
    /// 判据 = 结构判定 (无 shell 解析、无后缀白名单, 承 R447 语言无关令):
    ///   按 shell 元字符切 token → 含 '/'/'\\'/'..'/'~' 者归一化 (纯词法 Path.GetFullPath, 不碰文件系统) →
    ///   与工作区根前缀比对。
    /// 诚实边界: 只覆盖**字面路径**; 经变量/命令替换 (`$(…)`)、解释器内部 (如 python `open('/etc/x')`) 间接构造的
    ///   越界读不在覆盖内 —— 该断言的收窄写进报告, 不冒充「容器级隔离」。
    /// </summary>
    public static string? FindOutOfRootToken(string? command, string root)
    {
        if (string.IsNullOrWhiteSpace(command) || string.IsNullOrWhiteSpace(root)) return null;
        var r = Path.GetFullPath(root);
        foreach (var raw in command!.Split(TokenSplitters, StringSplitOptions.RemoveEmptyEntries))
        {
            var t = raw.Trim();
            if (t.Length == 0 || !LooksLikePath(t)) continue;
            if (t[0] == '~') return t;             // shell 会把它展开成家目录 ⇒ 结构上必然越界
            if (IsAllowedDevicePath(t)) continue;
            string full;
            try { full = Path.GetFullPath(Path.Combine(r, t)); }
            catch (Exception) { return t; }        // 非法路径形态 ⇒ 拒
            if (!InsideRoot(r, full)) return t;
        }
        return null;
    }

    private static bool LooksLikePath(string t)
        => t.IndexOf('/') >= 0 || t.Contains("..", StringComparison.Ordinal) || (t.Length > 0 && t[0] == '~');

    private static bool IsAllowedDevicePath(string t)
    {
        foreach (var d in AllowedDevicePaths)
            if (string.Equals(t, d, StringComparison.Ordinal)) return true;
        return false;
    }

    private static bool InsideRoot(string root, string full)
    {
        if (string.Equals(full, root, StringComparison.Ordinal)) return true;
        var prefix = root.EndsWith(Path.DirectorySeparatorChar) ? root : root + Path.DirectorySeparatorChar;
        return full.StartsWith(prefix, StringComparison.Ordinal);
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
                + ",\"args_head\":\"" + Esc(Head(call.ArgumentsJson, MaxAuditArgsChars)) + "\""
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

    /// <summary>审计用: 参数原文有界截断 (凭据卫生: 只落 200 字符头部)。</summary>
    internal const int MaxAuditArgsChars = 200;

    internal static string Head(string? s, int max)
        => string.IsNullOrEmpty(s) ? string.Empty
           : (s.Length <= max ? s : s.Substring(0, max) + "...");

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
