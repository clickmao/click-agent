using System;
using System.IO;
using Xunit;
using agent.gitops;

namespace agentframework.tests;

/// <summary>v0.18.0 G1 (R338): git 操作封装 — 临时仓内真 git 往返 (status/commit/diff/push once 卫生)。
/// 需要环境有 git (host 已具备)。测试自建临时仓库, 不触碰 AgentFramework 真实仓。</summary>
public class GitOperationsTests
{
    private static (string repo, GitOperations git) MakeRepo()
    {
        var dir = Path.Combine(Path.GetTempPath(), "af-git-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        var g = new GitOperations(dir);
        var init = g.Run("init", "-q");
        Assert.True(init.Ok, $"git init 失败: {init.ErrorSummary}");
        g.Run("config", "user.email", "test@local");
        g.Run("config", "user.name", "Test");
        return (dir, g);
    }

    [Fact]
    public void Commit_Roundtrip_StatusClean()
    {
        var (repo, g) = MakeRepo();
        File.WriteAllText(Path.Combine(repo, "a.txt"), "hello");
        var st = g.Status();
        Assert.Contains("a.txt", st.StdOut);
        var commit = g.StageAndCommit("test commit 1");
        Assert.True(commit.Ok, $"commit 失败: {commit.ErrorSummary}");
        var st2 = g.Status();
        Assert.DoesNotContain("a.txt", st2.StdOut); // 提交后干净
        var sha = g.HeadSha();
        Assert.True(sha.Ok);
        Assert.Equal(40, sha.StdOut.Trim().Length);
    }

    [Fact]
    public void Diff_ShowsUncommittedChange()
    {
        var (repo, g) = MakeRepo();
        File.WriteAllText(Path.Combine(repo, "b.txt"), "v1");
        g.StageAndCommit("base");
        File.WriteAllText(Path.Combine(repo, "b.txt"), "v2");
        var diff = g.Diff();
        Assert.Contains("-v1", diff.StdOut);
        Assert.Contains("+v2", diff.StdOut);
    }

    [Fact]
    public void EmptyCommit_Rejected()
    {
        var (repo, g) = MakeRepo();
        var r = g.Commit("   ");
        Assert.False(r.Ok);
    }

    [Fact]
    public void InvalidRepo_FailsGracefully()
    {
        var dir = Path.Combine(Path.GetTempPath(), "af-git-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir); // 非 git 仓
        var g = new GitOperations(dir);
        var r = g.Status();
        Assert.False(r.Ok);
    }

    [Fact]
    public void CommitHistory_VerifySha()
    {
        var (repo, g) = MakeRepo();
        File.WriteAllText(Path.Combine(repo, "c.txt"), "x");
        g.StageAndCommit("first");
        var sha1 = g.HeadSha().StdOut.Trim();
        File.WriteAllText(Path.Combine(repo, "c.txt"), "y");
        g.StageAndCommit("second");
        var sha2 = g.HeadSha().StdOut.Trim();
        Assert.NotEqual(sha1, sha2);
    }
}
