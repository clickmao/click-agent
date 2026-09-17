using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace agent.skills;

/// <summary>
/// L5 (t8–t12) 运行级验证: 语法校验 (py_compile) ≠ 能跑。本类把产物**真跑一遍**,
/// 给出进程级证据 (退出码/stderr/耗时), 让"已验证"三个字有物理含义。
///
/// 安全边界 (诚实声明):
/// - **默认跟随 py tool** (T4 决策 §11): 未设 `AGENTFRAMEWORK_PY_RUN` 时, 装了固定解释器
///   (scripts/fetch-py-tool.sh → explicit/pinned/managed) 才真跑; 显式 `=0|false|off` 一律关闭,
///   显式 `=1|true|on|yes` 无条件开。关闭时 RunAsync 直接拒绝 (Ran=false)。
/// - 只对 `.py` 产物开放 (非 python 产物不进这条路径); 解释器来源 (explicit/pinned/managed/path) 随结果返回, 可对账。
/// - 执行的是 LLM 生成的代码, **以当前进程用户权限运行** (无沙箱/无 seccomp) —— 只在可信产物+受控环境开启;
/// - 超时强制杀进程树; 输出按字符上限截断 (截断后继续排空管道, 避免子进程写满管道死锁);
/// - 零 shell: `ProcessStartInfo.ArgumentList` 直连 spawn, 路径含空格/引号不会被 shell 语义解析;
/// - 子进程继承环境但显式置 `AGENTFRAMEWORK_PY_RUN=0` (防自递归) 与 `PYTHONDONTWRITEBYTECODE=1` (不污染产物目录)。
/// </summary>
public static class PythonRunVerifier
{
    public const string EnableEnvName = "AGENTFRAMEWORK_PY_RUN";
    public const int DefaultTimeoutMs = 20_000;
    public const int DefaultMaxOutputChars = 8_000;
    public const int MaxConfiguredOutputChars = 200_000;

    /// <summary>运行级验证是否开启。
    /// T4 决策 (v0.22.0 exp9 §11): 未显式设置时 = **是否已装固定解释器** —— 装了 py tool
    /// (scripts/fetch-py-tool.sh: explicit/pinned/managed) 才默认真跑; 只有 PATH 兜底解释器时保持默认不跑,
    /// 免得"某个恰好存在的 python 跑过了"被当成结论 (不可复现的通过比不通过更危险)。
    /// 显式值语义: 1/true/on/yes = 开; 0/false/off/no/其它非空值 = 关 (fail-safe, 只有空值走默认)。</summary>
    public static bool IsEnabled(string? raw = null)
    {
        var v = raw ?? Environment.GetEnvironmentVariable(EnableEnvName);
        if (string.IsNullOrWhiteSpace(v))
            return PythonInterpreterResolver.HasPinnedInterpreter();
        return v.Trim().ToLowerInvariant() is "1" or "true" or "on" or "yes";
    }

    /// <summary>拒绝结果 (未启用/前置条件不满足) —— 不抛异常, 调用方按 Ran 判定。</summary>
    public static PythonRunResult Refused(string detail) =>
        new(false, -1, string.Empty, string.Empty, 0, false, false, detail);

    public static async Task<PythonRunResult> RunAsync(
        string scriptPath,
        string? pythonPath = null,
        string? workingDir = null,
        IReadOnlyList<string>? args = null,
        int timeoutMs = DefaultTimeoutMs,
        int maxOutputChars = DefaultMaxOutputChars,
        bool? explicitlyEnabled = null,
        CancellationToken ct = default)
    {
        // 闸门语义: 默认读环境变量; 调用方已自行闸门(如插件注入的 runGate)时可显式置位。
        if (!(explicitlyEnabled ?? IsEnabled()))
            return Refused($"运行级验证未启用 ({EnableEnvName} 显式关闭, 或本机无固定解释器; 见 exp9 §11)");
        if (string.IsNullOrWhiteSpace(scriptPath) || !File.Exists(scriptPath))
            return Refused($"脚本不存在: {scriptPath}");
        // T4 (§11): 闸门只对 .py 产物开放 —— 别的扩展名不是"python 产物", 不该进这条执行路径
        if (!scriptPath.EndsWith(".py", StringComparison.OrdinalIgnoreCase))
            return Refused($"只对 .py 产物开放真跑闸门 (路径={scriptPath})");

        var interp = PythonInterpreterResolver.Resolve(pythonPath);
        if (interp is null)
            return Refused("python 解释器不可用 (无固定解释器且 PATH 无 python3/python)");
        var python = interp.Exe;

        if (timeoutMs <= 0)
            timeoutMs = DefaultTimeoutMs;
        if (maxOutputChars <= 0)
            maxOutputChars = DefaultMaxOutputChars;
        if (maxOutputChars > MaxConfiguredOutputChars)
            maxOutputChars = MaxConfiguredOutputChars;

        var psi = new ProcessStartInfo
        {
            FileName = python,
            UseShellExecute = false,
            RedirectStandardError = true,
            RedirectStandardOutput = true,
            RedirectStandardInput = true,
            CreateNoWindow = true,
        };
        psi.ArgumentList.Add("-I"); // 隔离模式: 忽略 PYTHON* 环境变量与用户 site-packages (可复现)
        // R371 真缺陷 (D6, 假阴性): 下面会把子进程 cwd 切到脚本所在目录, 若此处传相对路径
        // (插件用 "data/artifacts/..." 就是相对路径) → 相对路径在子进程里二次拼接 → 文件不存在 →
        // python 以 exit=2 秒退, 运行级验证结论错误地显示"失败"。故**必须**用绝对路径。
        psi.ArgumentList.Add(Path.GetFullPath(scriptPath));
        if (args is not null)
        {
            foreach (var a in args)
                psi.ArgumentList.Add(a);
        }
        var dir = workingDir;
        if (string.IsNullOrWhiteSpace(dir))
        {
            try { dir = Path.GetDirectoryName(Path.GetFullPath(scriptPath)); }
            catch { dir = null; }
        }
        if (!string.IsNullOrWhiteSpace(dir) && Directory.Exists(dir))
            psi.WorkingDirectory = dir;
        psi.Environment["AGENTFRAMEWORK_PY_RUN"] = "0";      // 防自递归
        psi.Environment["PYTHONDONTWRITEBYTECODE"] = "1";    // 不写 __pycache__
        psi.Environment["PYTHONIOENCODING"] = "utf-8";

        var sw = Stopwatch.StartNew();
        Process? p = null;
        try
        {
            p = new Process { StartInfo = psi };
            p.Start();
            try { p.StandardInput.Close(); } catch { /* 无需 stdin */ }

            var outTask = ReadCappedAsync(p.StandardOutput, maxOutputChars);
            var errTask = ReadCappedAsync(p.StandardError, maxOutputChars);

            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(timeoutMs);
            var timedOut = false;
            try
            {
                await p.WaitForExitAsync(cts.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                timedOut = true;
                try { p.Kill(entireProcessTree: true); } catch { /* 退出竞态 */ }
                try { await p.WaitForExitAsync(CancellationToken.None).ConfigureAwait(false); }
                catch { /* ignore */ }
            }
            var o = await outTask.ConfigureAwait(false);
            var e = await errTask.ConfigureAwait(false);
            sw.Stop();
            var code = timedOut ? -1 : SafeExitCode(p);
            var detail = timedOut
                ? $"运行超时 ({timeoutMs}ms) → 已杀进程树; interp={interp.Source}:{python}"
                : $"exit={code}; stdout={o.Text.Length}ch{(o.Truncated ? "(截断)" : "")}; stderr={e.Text.Length}ch{(e.Truncated ? "(截断)" : "")}; interp={interp.Source}:{python}";
            return new PythonRunResult(true, code, o.Text, e.Text, sw.ElapsedMilliseconds,
                timedOut, o.Truncated || e.Truncated, detail, python);
        }
        catch (Exception ex)
        {
            sw.Stop();
            return new PythonRunResult(false, -1, string.Empty, string.Empty, sw.ElapsedMilliseconds,
                false, false, $"运行失败: {ex.Message}", python);
        }
        finally
        {
            p?.Dispose();
        }
    }

    private static int SafeExitCode(Process p)
    {
        try { return p.ExitCode; } catch { return -1; }
    }

    /// <summary>
    /// 有界读取: 到达上限后**继续排空**剩余字节 (只计数不存储), 否则子进程写满管道会死锁到超时。
    /// </summary>
    private static async Task<(string Text, bool Truncated)> ReadCappedAsync(StreamReader reader, int maxChars)
    {
        var sb = new StringBuilder(Math.Min(maxChars, 8192));
        var buf = new char[4096];
        var truncated = false;
        while (true)
        {
            int n;
            try { n = await reader.ReadAsync(buf.AsMemory(0, buf.Length)).ConfigureAwait(false); }
            catch { break; }
            if (n <= 0)
                break;
            if (sb.Length < maxChars)
            {
                var room = maxChars - sb.Length;
                if (n <= room)
                    sb.Append(buf, 0, n);
                else
                {
                    sb.Append(buf, 0, room);
                    truncated = true;
                }
            }
            else
            {
                truncated = true; // 排空模式
            }
        }
        return (sb.ToString(), truncated);
    }
}
