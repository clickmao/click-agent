using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.contract;

namespace agent.r1;

/// <summary>
/// R1 管道 · 计划执行器（窄腰：工具面只有 write_file / run，与 tool_menu 逐条对齐）。
/// 双保险：闸已判过 scope，执行器**再判一次**（闸与执行器非同源 ⇒ 任一漏判不致命）。
/// 写侧一律 UTF8Encoding(false) 去 BOM；run 侧超时即杀并记 -9。
/// </summary>
public static class PlanExecutor
{
    public static async Task<PlanExecutorResult> RunAsync(IReadOnlyList<PlanStep> plan, R1Options opt, CancellationToken ct)
    {
        var steps = new List<StepOutcome>();
        Directory.CreateDirectory(opt.SandboxRoot);
        var root = Path.GetFullPath(opt.SandboxRoot);

        foreach (var st in plan)
        {
            if (string.IsNullOrEmpty(st.Id))
            {
                return new PlanExecutorResult(4, "plan", "步骤缺 id", steps);
            }

            if (st.Tool == "none")
            {
                steps.Add(StepOutcome.None(st.Id));
                continue;
            }

            if (st.Tool == "write_file")
            {
                if (string.IsNullOrEmpty(st.Path))
                {
                    return new PlanExecutorResult(4, "plan", "write_file 缺 path (step " + st.Id + ")", steps);
                }
                var full = Path.GetFullPath(Path.Combine(root, st.Path));
                if (!IsInside(full, root))
                {
                    return new PlanExecutorResult(4, "scope", "路径逃出沙箱: " + st.Path, steps);
                }
                var dir = Path.GetDirectoryName(full);
                if (!string.IsNullOrEmpty(dir))
                {
                    Directory.CreateDirectory(dir);
                }
                var bytes = new UTF8Encoding(false).GetBytes(st.Content ?? string.Empty);
                await File.WriteAllBytesAsync(full, bytes, ct);
                steps.Add(StepOutcome.Write(st.Id, st.Path, R1Hash.OfBytes(bytes), bytes.Length));
                continue;
            }

            if (st.Tool == "run")
            {
                if (string.IsNullOrEmpty(st.Cmd))
                {
                    return new PlanExecutorResult(4, "plan", "run 缺 cmd (step " + st.Id + ")", steps);
                }
                var sw = Stopwatch.StartNew();
                var r = await BashAsync(st.Cmd, root, opt.StepTimeoutSeconds, ct);
                sw.Stop();
                steps.Add(StepOutcome.Run(st.Id, r.Rc, R1Text.Tail(r.Stdout, 400), R1Text.Tail(r.Stderr, 400), (int)sw.ElapsedMilliseconds));

                var expect = st.ExpectStdout ?? string.Empty;
                if (!string.IsNullOrEmpty(expect) && r.Stdout.TrimEnd() != expect.TrimEnd())
                {
                    // R533: 证据义务 —— 期望/实测两侧都进 Reason, 使回灌修复轮拿到可判别的差量 (禁只说「不符」)。
                    return new PlanExecutorResult(5, "expect_stdout",
                        "step " + st.Id + " stdout 与 expect_stdout 不符 (rc=" + r.Rc
                        + ", 期望=`" + R1Text.Tail(expect, 120) + "`, 实测=`" + R1Text.Tail(r.Stdout.TrimEnd(), 120) + "`)", steps);
                }
                if (r.Rc != 0)
                {
                    return new PlanExecutorResult(5, "run_rc", "step " + st.Id + " rc=" + r.Rc, steps);
                }
                continue;
            }

            return new PlanExecutorResult(4, "plan", "非白名单工具: " + st.Tool + " (step " + st.Id + ")", steps);
        }

        return new PlanExecutorResult(0, "executed", "全部步骤执行完毕 (" + steps.Count + " 步)", steps);
    }

    private static bool IsInside(string full, string root)
    {
        if (string.Equals(full, root, StringComparison.Ordinal))
        {
            return true;
        }
        return full.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.Ordinal);
    }

    private static async Task<(int Rc, string Stdout, string Stderr)> BashAsync(string cmd, string cwd, int timeoutSec, CancellationToken ct)
    {
        var psi = new ProcessStartInfo
        {
            FileName = "/bin/bash",
            WorkingDirectory = cwd,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        psi.ArgumentList.Add("-lc");
        psi.ArgumentList.Add(cmd);

        using var p = new Process { StartInfo = psi };
        var so = new StringBuilder();
        var se = new StringBuilder();
        p.OutputDataReceived += (_, e) => { if (e.Data is not null) { so.AppendLine(e.Data); } };
        p.ErrorDataReceived += (_, e) => { if (e.Data is not null) { se.AppendLine(e.Data); } };

        p.Start();
        p.BeginOutputReadLine();
        p.BeginErrorReadLine();

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(TimeSpan.FromSeconds(timeoutSec));
        try
        {
            await p.WaitForExitAsync(cts.Token);
        }
        catch (OperationCanceledException)
        {
            try
            {
                p.Kill(true);
            }
            catch (InvalidOperationException)
            {
                // 进程已退出 ⇒ 无需处理
            }
            return (-9, so.ToString(), se.ToString() + "\n[超时 " + timeoutSec + "s ⇒ 杀进程]");
        }

        p.WaitForExit();
        return (p.ExitCode, so.ToString(), se.ToString());
    }
}
