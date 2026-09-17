using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace agent.r1;

/// <summary>
/// R1 管道 · 公开用例**独立回放**（产物侧自检）。
///
/// 判据与外部隐藏用例判分器**同语义**（逐字节比 stdout、rc 必须为 0、尾换行归一），
/// 但输入/期望全部来自题面机械抽取 ⇒ 复现的是**题面契约**，不是模型自述。
/// 与 <c>expect_stdout</c>（模型自撰期望）的区别即本探针的全部价值：
/// R542 实测 rc=0 的 4 个 r1 臂产物仅 43–55/58 ⇒ 「模型自述完成」不是正确性证据。
///
/// 证据纪律：失败项带 分组 id / 输入 / 期望 / 实测 rc+stdout+stderr（各有界），
/// 供回灌修复轮与台账消费；超出上限的失败项**计数**仍然给出（不静默截断总数）。
/// </summary>
public static class PublicExampleProbe
{
    public const int MaxFailureLines = 8;
    public const int EvidenceChars = 160;

    public static async Task<PublicProbeResult> RunAsync(PublicExampleSet set, string sandboxRoot, int timeoutSec, CancellationToken ct)
    {
        if (set.Examples.Count == 0)
        {
            return PublicProbeResult.Skipped("no_examples");
        }
        if (string.IsNullOrEmpty(sandboxRoot) || !Directory.Exists(sandboxRoot))
        {
            return PublicProbeResult.Skipped("sandbox_missing");
        }

        var total = Math.Min(set.Examples.Count, PublicExampleExtractor.MaxExamples);
        var lim = Math.Min(Math.Max(timeoutSec, 5), 60);
        var failures = new List<string>();
        var failed = 0;
        var pycPrefix = Path.Combine(Path.GetTempPath(), "r1probe-pyc-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(pycPrefix);
        try
        {
            for (var i = 0; i < total; i++)
            {
                ct.ThrowIfCancellationRequested();
                var ex = set.Examples[i];
                var cmd = set.CommandPrefix + ex.GameId;
                var r = await BashAsync(cmd, sandboxRoot, ex.Input + "\n", lim, ct, pycPrefix).ConfigureAwait(false);
                // 与隐藏用例判分器同语义：rc==0 ∧ stdout.strip('\n') == expected.strip('\n')
                var ok = r.Rc == 0 && r.Stdout.Trim('\n') == ex.Expected.Trim('\n');
                if (ok)
                {
                    continue;
                }
                failed++;
                if (failures.Count < MaxFailureLines)
                {
                    failures.Add("分组 " + ex.GameId + " | 输入=`" + One(ex.Input) + "` | 期望=`" + One(ex.Expected)
                        + "` | 实测 rc=" + r.Rc + " stdout=`" + One(r.Stdout) + "` stderr尾=`" + One(r.Stderr) + "`");
                }
            }
        }
        finally
        {
            try
            {
                Directory.Delete(pycPrefix, true);
            }
            catch (IOException)
            {
                // 缓存目录清理失败不影响读数（它不在产物树内）
            }
        }

        return new PublicProbeResult(true, failed == 0 ? "public_examples_pass" : "public_examples_failed",
            total, failed, failures);
    }

    private static string One(string s)
    {
        var flat = (s ?? string.Empty).Replace("\r", " ").Replace("\n", "⏎");
        flat = flat.Trim().Trim('⏎').Trim();
        return flat.Length <= EvidenceChars ? flat : "…" + flat.Substring(flat.Length - EvidenceChars);
    }

    private static async Task<(int Rc, string Stdout, string Stderr)> BashAsync(
        string cmd, string cwd, string stdin, int timeoutSec, CancellationToken ct, string pycPrefix)
    {
        var psi = new ProcessStartInfo
        {
            FileName = "/bin/bash",
            WorkingDirectory = cwd,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        psi.ArgumentList.Add("-lc");
        psi.ArgumentList.Add(cmd);

        // 与被测判分器同语义的最小环境（判分器就是这么跑的）：
        //  · PYTHONDONTWRITEBYTECODE=1 ⇒ 不在产物树里落字节码；
        //  · PYTHONPYCACHEPREFIX = **每次回放独立空目录** ⇒ 即便产物树里已有陈旧字节码
        //    （同秒同长度改写会让 mtime+size 校验失效 ⇒ 旧 pyc 被复用），回放也不读它 ——
        //    否则「回放不过」会变成字节码缓存的产物而不是实现的产物。
        psi.Environment.Clear();
        psi.Environment["PATH"] = "/usr/local/bin:/usr/bin:/bin";
        psi.Environment["LANG"] = "C.UTF-8";
        psi.Environment["HOME"] = cwd;
        psi.Environment["PYTHONPATH"] = cwd;
        psi.Environment["PYTHONDONTWRITEBYTECODE"] = "1";
        psi.Environment["PYTHONPYCACHEPREFIX"] = pycPrefix;

        using var p = new Process { StartInfo = psi };
        var so = new StringBuilder();
        var se = new StringBuilder();
        p.OutputDataReceived += (_, e) => { if (e.Data is not null) { so.AppendLine(e.Data); } };
        p.ErrorDataReceived += (_, e) => { if (e.Data is not null) { se.AppendLine(e.Data); } };
        p.Start();
        p.BeginOutputReadLine();
        p.BeginErrorReadLine();

        try
        {
            await p.StandardInput.WriteAsync(stdin).ConfigureAwait(false);
            await p.StandardInput.FlushAsync().ConfigureAwait(false);
            p.StandardInput.Close();
        }
        catch (IOException)
        {
            // 子进程已退出 ⇒ 写 stdin 失败属正常路径（rc/stdout 仍可判）
        }

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(TimeSpan.FromSeconds(timeoutSec));
        try
        {
            await p.WaitForExitAsync(cts.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            try
            {
                p.Kill(true);
            }
            catch (InvalidOperationException)
            {
                // 已退出
            }
            return (-9, so.ToString(), se.ToString() + "\n[公开用例回放超时 " + timeoutSec + "s ⇒ 杀进程]");
        }

        p.WaitForExit();
        return (p.ExitCode, so.ToString(), se.ToString());
    }
}
