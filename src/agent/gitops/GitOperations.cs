using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;

namespace agent.gitops;

/// <summary>
/// v0.18.0 G1 (R338, 差距分析): git 操作封装 — 让 agent 自身能完成产品迭代闭环的 git 步骤
/// (status/diff/commit/push)。现状: 框架内无任何 git 调用 (全仓 grep 零调用点), 迭代产物提交依赖外部。
/// 凭据卫生 (用户钦定铁律): push 只接受一次性 URL (调用方经环境/参数注入), 绝不写 git config;
/// 用后可从 remote 清除 (ResetRemote)。输出 UTF-8 (C# 默认 UTF-16 管道坑: 需重定向 stdout 字节解码)。
/// AOT 安全: Process + BCL, 禁反射。
/// </summary>
public sealed class GitOperations
{
    private readonly string _repoDir;
    private readonly string _git;

    public GitOperations(string repoDir)
    {
        _repoDir = Path.GetFullPath(repoDir);
        _git = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_GIT") ?? "git";
    }

    public sealed class GitResult
    {
        public int ExitCode { get; init; }
        public string StdOut { get; init; } = "";
        public string StdErr { get; init; } = "";
        public bool Ok => ExitCode == 0;
        public string ErrorSummary => StdErr.Length > 200 ? StdErr[..200] + "…" : StdErr;
    }

    public GitResult Run(params string[] args)
    {
        var psi = new ProcessStartInfo
        {
            FileName = _git,
            WorkingDirectory = _repoDir,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
        };
        foreach (var a in args) psi.ArgumentList.Add(a);
        try
        {
            using var p = Process.Start(psi);
            if (p is null) return new GitResult { ExitCode = -1, StdErr = "git 启动失败" };
            var so = p.StandardOutput.ReadToEnd();
            var se = p.StandardError.ReadToEnd();
            if (!p.WaitForExit(30_000))
            {
                try { p.Kill(entireProcessTree: true); } catch { }
                return new GitResult { ExitCode = -2, StdErr = "git 超时 (30s)" };
            }
            return new GitResult { ExitCode = p.ExitCode, StdOut = so, StdErr = se };
        }
        catch (Exception ex)
        {
            return new GitResult { ExitCode = -3, StdErr = ex.Message };
        }
    }

    public GitResult Status() => Run("status", "--short");
    public GitResult DiffStat() => Run("diff", "--stat");
    public GitResult Diff() => Run("diff");

    public GitResult Commit(string message)
    {
        if (string.IsNullOrWhiteSpace(message)) return new GitResult { ExitCode = -4, StdErr = "commit message 为空" };
        return Run("commit", "-q", "-m", message);
    }

    /// <summary>暂存并提交 (产物闭环常用: git add -A + commit)。</summary>
    public GitResult StageAndCommit(string message)
    {
        var add = Run("add", "-A");
        if (!add.Ok) return add;
        return Commit(message);
    }

    /// <summary>一次性 URL push (凭据卫生: 只 push 不写 config; 推完可选 ClearRemote)。</summary>
    public GitResult PushOnce(string url, string branch = "main")
    {
        // 卫生检查: URL 含 token 时绝不进 git config (只作为命令行参数, 进程结束后即失)
        return Run("push", url, branch);
    }

    public GitResult ClearRemote() => Run("remote", "remove", "origin-once");

    public GitResult HeadSha() => Run("rev-parse", "HEAD");

    public GitResult RemoteHeadSha(string url, string branch = "main")
        => Run("ls-remote", url, $"refs/heads/{branch}");

    /// <summary>commit 后推远端并复核 sha (与 Hermes 侧流程同构: 推后 local vs remote 比对)。</summary>
    public string VerifyPush(string url, string branch = "main")
    {
        var local = HeadSha();
        if (!local.Ok) return $"本地 sha 失败: {local.ErrorSummary}";
        var remote = RemoteHeadSha(url, branch);
        if (!remote.Ok) return $"远端 sha 失败: {remote.ErrorSummary}";
        var l = local.StdOut.Trim();
        var r = remote.StdOut.Split('\t')[0].Trim();
        return l == r ? $"MATCH {l[..Math.Min(12, l.Length)]}" : $"MISMATCH local={l[..12]} remote={r[..12]}";
    }
}
