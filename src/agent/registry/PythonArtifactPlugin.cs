using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.skills;

namespace agent.registry;

/// <summary>
/// Python 产物报告 (审计/前端/教训复用; 单行可序列化)。
/// </summary>
public sealed record PythonArtifactReport(
    string Path,
    string Language,
    int Bytes,
    string Sha256Short,
    bool CompileValid,
    int ExitCode,
    string Detail,
    long AtUnixMs,
    bool Ran = false,          // L5: 是否真的执行过 (运行级验证)
    int RunExitCode = -1,
    long RunElapsedMs = 0,
    bool RunTimedOut = false,
    // R374: 校验/运行输出摘要 (尾部保留) — 让"失败原因"成为可观测事实, 而非只有一个 exit 码。
    string OutputExcerpt = "");

/// <summary>
/// Python 产物台账 (R368): 线程安全, 记录本进程内所有落盘+校验结果。
/// 宿主/CLI/前端快照可读 — 让"机器校验"成为可观测事实, 而不是隐式行为。
/// </summary>
public sealed class PythonArtifactLedger
{
    private readonly List<PythonArtifactReport> _items = new();
    private long _version;

    /// <summary>单调递增版本号 (变化 = 有新报告; 前端轮询增量用)。</summary>
    public long Version => Interlocked.Read(ref _version);
    public void Add(PythonArtifactReport r) { lock (_items) _items.Add(r); Interlocked.Increment(ref _version); }
    public IReadOnlyList<PythonArtifactReport> Snapshot() { lock (_items) return _items.ToArray(); }
}

/// <summary>
/// Python 落盘 + 机器校验区段插件 (R368, 用户钦定: "内置个 PY 和 PY 执行插件")。
///
/// 语义: LLM 回复里的 ```python 段不再是"只存在于聊天里的文本", 而是
///   ① 落盘为可交付文件 (data/artifacts/*.py, 内容 SHA256 前 8 位命名 → 幂等)
///   ② 交给本机 python3 做 `-m py_compile` 机器校验 (真实进程, 非 LLM 自证)
///   ③ 结论写台账 (PythonArtifactLedger) + telemetry 点 script_artifact
///
/// 诚实边界: 默认只做语法/编译级 (py_compile), 不等于"逻辑正确"; 失败原文回写台账不静默。
///          L5 (t8–t12): 若开启 AGENTFRAMEWORK_PY_RUN, 语法通过后**真跑一遍**并把
///          退出码/耗时/超时/stderr 写回报告 (Ran/RunExitCode/RunElapsedMs/RunTimedOut) —— 默认关闭。
/// 输出契约: 恒等返回段内容 (不改写 LLM 文本, 避免污染代码围栏);
///          校验结论经台账/telemetry 暴露 → 宿主展示, 前端可订阅。
/// 非 python 语言段零损耗透传。
/// </summary>
public sealed class PythonArtifactPlugin : IResponseSegmentPlugin, IArtifactCheckSource
{
    private static readonly string[] PythonLangs = { "python", "py", "python3", "python3.11", "python3.12" };

    private readonly string _artifactsRoot;
    private readonly PythonArtifactLedger _ledger;
    private readonly Func<string?> _pythonResolver;
    private readonly Func<bool> _runGate;
    private readonly bool _enabled;

    public PythonArtifactPlugin(
        PythonArtifactLedger ledger,
        string? artifactsRoot = null,
        Func<string?>? pythonResolver = null,
        Func<bool>? runGate = null)
    {
        _ledger = ledger;
        _artifactsRoot = string.IsNullOrWhiteSpace(artifactsRoot)
            ? Path.Combine("data", "artifacts")
            : artifactsRoot!;
        _pythonResolver = pythonResolver ?? DefaultPythonResolver;
        // L5: 运行级验证闸门 (构造时快照 AGENTFRAMEWORK_PY_RUN; 测试可注入 → 行为可断言)。
        // 快照而非动态读: 避免同进程内别的用例改 env 造成本插件行为漂移。
        if (runGate is not null)
        {
            _runGate = runGate;
        }
        else
        {
            var on = PythonRunVerifier.IsEnabled();
            _runGate = () => on;
        }
        // 逃生阀: 环境变量可关 (默认开 — 用户需求是"一定要揪出来")
        _enabled = !string.Equals(
            Environment.GetEnvironmentVariable("AGENTFRAMEWORK_PY_ARTIFACT"),
            "off", StringComparison.OrdinalIgnoreCase);
    }

    public string Name => "python-artifact";

    // R374 (D3): 待回流校验结论队列 (取即清)。并发安全: 插件可能被多会话/子任务并发调用。
    private readonly ConcurrentQueue<ArtifactCheck> _pendingChecks = new();

    /// <summary>取走自上次调用以来新增的校验结论 (含通过项 — 复检据此判定"修好了")。</summary>
    public IReadOnlyList<ArtifactCheck> DrainNewChecks()
    {
        var list = new List<ArtifactCheck>();
        while (_pendingChecks.TryDequeue(out var c))
            list.Add(c);
        return list;
    }

    public IReadOnlySet<SegmentKind> Consumes { get; } =
        new HashSet<SegmentKind> { SegmentKind.Code };

    /// <summary>是否 python 代码段 (宿主/审计可复用判定)。</summary>
    public static bool IsPythonSegment(ResponseSegment segment) =>
        segment.Kind == SegmentKind.Code &&
        segment.Language is not null &&
        PythonLangs.Contains(segment.Language.ToLowerInvariant());

    public async Task<string> HandleAsync(ResponseSegment segment, CancellationToken ct = default)
    {
        if (!_enabled || !IsPythonSegment(segment) || string.IsNullOrWhiteSpace(segment.Content))
            return segment.Content;

        var content = segment.Content;
        var bytes = Encoding.UTF8.GetBytes(content);
        var sha = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
        var shortSha = sha[..8];

        var (report, check) = await PersistAndVerifyAsync(content, bytes.Length, sha, segment.Language!, ct)
            .ConfigureAwait(false);
        _ledger.Add(report);
        // R374 (D3): 校验结论排队待回流 (含通过项 — 复检需要"通过"证据才能判定已修复)。
        if (ArtifactRepairPolicy.IsEnabled())
            _pendingChecks.Enqueue(check);
        agent.config.AgentTelemetry.Emit("script_artifact", "python-artifact",
            ("path", report.Path), ("bytes", report.Bytes), ("sha8", report.Sha256Short),
            ("compile_valid", report.CompileValid), ("exit", report.ExitCode),
            // R371 D4-b: **机制归因** — fenced(模型自带围栏) vs heuristic(无围栏启发式提升)。
            // 没有这个字段, "artifact 命中率" 上升无法归因到 D4-b (真机 RUN1/2 是否走启发式无从区分)。
            ("origin", segment.Promoted ? "heuristic" : "fenced"));
        return content; // 恒等: 不改写 LLM 文本
    }

    private async Task<(PythonArtifactReport Report, ArtifactCheck Check)> PersistAndVerifyAsync(
        string content, int byteCount, string sha, string language, CancellationToken ct)
    {
        var shortSha = sha[..8];
        var now = DateTimeOffset.UtcNow;
        var path = string.Empty;
        string detail;
        var exitCode = -1;
        var valid = false;
        var ran = false;
        var runExit = -1;
        long runMs = 0;
        var runTimedOut = false;
        // R374: 失败原因文本 (编译 stderr 或 运行 stderr/stdout) — 此前只留一个 exit 码, 信息在此处被丢弃。
        var output = string.Empty;

        try
        {
            Directory.CreateDirectory(_artifactsRoot);
            // R370 修潜伏缺陷: 旧命名 py_yyyyMMdd_HHmmss_sha8 含时间戳 → 同一内容跨秒产出变两个文件,
            // 与"内容寻址/幂等同名"契约冲突 (R368 用例在跨秒边界随机失败, 本机高负载时必现)。
            // 纯内容寻址: 同内容恒定同路径 (16 hex = 64bit, 避免 8hex/32bit 的碰撞覆盖风险)。
            path = Path.Combine(_artifactsRoot, $"py_{sha[..16]}.py");
            if (!File.Exists(path))
                await File.WriteAllTextAsync(path, content, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false), ct)
                    .ConfigureAwait(false);

            var check = await PythonScriptValidator.ValidateAsync(path, _pythonResolver(), ct).ConfigureAwait(false);
            valid = check.Valid;
            exitCode = check.ExitCode;
            detail = check.Detail;
            output = check.Detail; // 编译失败时 Detail 即 py_compile 的错误输出

            // L5: 语法通过且闸门开启 → 真跑一遍 (进程级证据: 退出码/耗时/stderr)
            if (valid && _runGate())
            {
                // R371: 产物自带无头自测入口时, 用 --selftest 跑 (否则交互式程序必然卡到超时,
                // 验证结论退化为"超时"而不是"对错") — 选参策略保守: 只认显式出现的 --selftest。
                var runArgs = ArtifactCheck.MentionsSelfTest(content)
                    ? new[] { "--selftest" }
                    : Array.Empty<string>();
                var run = await PythonRunVerifier.RunAsync(path, _pythonResolver(), workingDir: null, args: runArgs,
                    timeoutMs: PythonRunVerifier.DefaultTimeoutMs, maxOutputChars: 2000,
                    explicitlyEnabled: true, ct: ct).ConfigureAwait(false);
                ran = run.Ran;
                runExit = run.ExitCode;
                runMs = run.ElapsedMs;
                runTimedOut = run.TimedOut;
                // R374: 真跑输出回流 (stderr 优先, stdout 补充; 两路各自已被 verifier 限幅)。
                output = ComposeRunOutput(run.StdOut, run.StdErr);
                var runNote = run.Ran
                    ? $"run: {run.Detail}" + (string.IsNullOrWhiteSpace(run.StdErr) ? string.Empty : $" stderr={Truncate(run.StdErr.Trim(), 200)}")
                    : $"run(未执行): {run.Detail}";
                detail = $"{detail} | {runNote}";
                agent.config.AgentTelemetry.Emit("script_run", "python-artifact",
                    ("path", path), ("ran", run.Ran), ("exit", run.ExitCode),
                    ("ms", run.ElapsedMs), ("timed_out", run.TimedOut), ("truncated", run.OutputTruncated));
            }
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            detail = $"落盘/校验异常: {ex.Message}";
        }

        var report = new PythonArtifactReport(
            path, language, byteCount, shortSha, valid, exitCode,
            Truncate(detail, 300), now.ToUnixTimeMilliseconds(),
            ran, runExit, runMs, runTimedOut,
            Truncate(output, 1200));
        // 回流用结论: 输出最多 6000 字符 (回灌模型的量级由策略再裁)。
        var artifactCheck = new ArtifactCheck(
            path, language, content, valid, exitCode, ran, runExit, runTimedOut, Truncate(output, 6000));
        return (report, artifactCheck);
    }

    private static string? DefaultPythonResolver()
    {
        var env = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_PYTHON");
        if (!string.IsNullOrWhiteSpace(env) && File.Exists(env))
            return env;
        // agent.skills 的 FindOnPath 是 internal (跨程序集不可见) → 本插件自带等价实现。
        // 跨平台: Windows 需试 .exe/.cmd/.bat 后缀; Unix 直接查可执行文件。
        var pathVar = Environment.GetEnvironmentVariable("PATH");
        if (string.IsNullOrEmpty(pathVar))
            return null;
        var exts = OperatingSystem.IsWindows()
            ? new[] { ".exe", ".cmd", ".bat", string.Empty }
            : new[] { string.Empty };
        foreach (var dir in pathVar.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            foreach (var name in new[] { "python3", "python" })
            foreach (var ext in exts)
            {
                var candidate = Path.Combine(dir, name + ext);
                if (File.Exists(candidate))
                    return candidate;
            }
        }
        return null;
    }

    /// <summary>R374: 运行输出合并 (stderr 在前 — 错误优先; 空则省略该段)。</summary>
    private static string ComposeRunOutput(string? stdout, string? stderr)
    {
        var err = stderr?.Trim() ?? string.Empty;
        var outText = stdout?.Trim() ?? string.Empty;
        if (err.Length == 0) return outText;
        if (outText.Length == 0) return err;
        return $"[stderr]\n{err}\n[stdout]\n{outText}";
    }

    private static string Truncate(string s, int max) =>
        string.IsNullOrEmpty(s) ? string.Empty : (s.Length <= max ? s : s[..max] + "…");
}
