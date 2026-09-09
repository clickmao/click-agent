using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Threading.Tasks;

namespace agent.skills;

/// <summary>v0.17.2-b: py_compile 验证结果。</summary>
public sealed record PythonValidationResult(bool Valid, string Detail, int ExitCode);

/// <summary>
/// v0.17.2-b (用户钦定: "CLI 验证 PY 正确后交给插件服务"): py 脚本验证门 —
/// 真实 `python3 -m py_compile` 语法校验 (进程级, AOT 安全, 不内嵌 Python)。
/// 失败 = 拒绝执行 + 教训 Record (script-invalid:&lt;name&gt;)。
/// </summary>
public static class PythonScriptValidator
{
    public const int CompileTimeoutMs = 30_000;

    public static async Task<PythonValidationResult> ValidateAsync(string scriptPath, CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(scriptPath) || !File.Exists(scriptPath))
            return new PythonValidationResult(false, $"脚本不存在: {scriptPath}", -1);
        var python = SkillScriptRunner.FindOnPath("python3") ?? SkillScriptRunner.FindOnPath("python");
        if (python is null)
            return new PythonValidationResult(false, "python3 解释器不可用 (PATH 无 python3/python)", -2);

        var psi = new ProcessStartInfo
        {
            FileName = python,
            Arguments = $"-m py_compile \"{scriptPath}\"",
            UseShellExecute = false,
            RedirectStandardError = true,
            RedirectStandardOutput = true,
            CreateNoWindow = true,
        };
        try
        {
            using var p = new Process { StartInfo = psi };
            p.Start();
            var errTask = p.StandardError.ReadToEndAsync();
            var outTask = p.StandardOutput.ReadToEndAsync();
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(CompileTimeoutMs);
            try
            {
                await p.WaitForExitAsync(cts.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                try { p.Kill(entireProcessTree: true); } catch { /* 已退出竞态 */ }
                return new PythonValidationResult(false, "py_compile 超时 (30s)", -3);
            }
            await Task.WhenAll(errTask, outTask).ConfigureAwait(false);
            var stderr = errTask.Result?.Trim() ?? string.Empty;
            var code = p.ExitCode;
            if (code == 0)
                return new PythonValidationResult(true, "ok", 0);
            return new PythonValidationResult(false,
                string.IsNullOrEmpty(stderr) ? "语法错误 (stderr 空)" : Truncate(stderr, 600), code);
        }
        catch (Exception ex)
        {
            return new PythonValidationResult(false, $"py_compile 启动失败: {ex.Message}", -4);
        }
    }

    private static string Truncate(string s, int max) => s.Length <= max ? s : s[..max] + "…";
}
