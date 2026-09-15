using System;
using System.IO;
using System.Text;
using agent.context;
using agent.core;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R462 召回-现实一致性闸 + 语言无关文本探针 —— 单测。
///
/// 依据 (R460/R461 实发): 召回块声称 `stats.txt=chars=14`, 而当前工作区无该文件 ⇒ 模型据此回「已写入 chars=15」= 编造。
/// 判据形 (机检): 凡含路径样 token 的子句必带 [核验✓ 现存 N B] / [核验✗ …] 标签;
///   无 root/异常 ⇒ fail-safe 原样返回; 越界路径不探测; 幂等。
/// 语言无关令 (R447): 探针判定零后缀白名单 —— 后缀集只在显式配置时生效。
/// </summary>
public sealed class RecallRealityGateTests
{
    private static string NewTempRoot()
    {
        var dir = Path.Combine(Path.GetTempPath(), "r462-gate-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(dir);
        return dir;
    }

    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        Assert.NotNull(dir);
        return dir!.FullName;
    }

    /// <summary>语言标签集来自**数据文件** (可配) —— 判定器源码零硬编码 (承 R447 语言无关令)。</summary>
    private static string[] LanguageTags()
    {
        var p = Path.Combine(RepoRoot(), "config", "base", "language-tags.txt");
        Assert.True(File.Exists(p), "语言标签数据文件缺失: " + p);
        return File.ReadAllLines(p, Encoding.UTF8)
            .Select(l => l.Trim())
            .Where(l => l.Length > 0 && !l.StartsWith('#'))
            .ToArray();
    }

    // ---------- 面 1: 召回事实 vs 现实 ----------

    [Fact]
    public void Verify_MissingArtifact_TaggedAsNotExisting()
    {
        var root = NewTempRoot();
        var block = "【已完成】把三行合并成 stats.txt=chars=14 (write_file 完成)";

        var outp = RecallRealityGate.Verify(block, root);

        Assert.Contains(RecallRealityGate.BadTag, outp, StringComparison.Ordinal);
        Assert.Contains("不存在", outp, StringComparison.Ordinal);
        Assert.Contains("stats.txt", outp, StringComparison.Ordinal); // 原声明保留可见 (不掩事实)
    }

    [Fact]
    public void Verify_ExistingArtifact_TaggedWithRealByteCount()
    {
        var root = NewTempRoot();
        var file = Path.Combine(root, "stats.txt");
        File.WriteAllText(file, "chars=14\n", new UTF8Encoding(false));
        var real = new FileInfo(file).Length;
        var block = "【已完成】stats.txt=chars=14";

        var outp = RecallRealityGate.Verify(block, root);

        Assert.Contains(RecallRealityGate.OkTag, outp, StringComparison.Ordinal);
        Assert.Contains($"现存 {real}B", outp, StringComparison.Ordinal);
        Assert.DoesNotContain(RecallRealityGate.BadTag, outp, StringComparison.Ordinal);
    }

    [Fact]
    public void Verify_NoPathToken_Untouched()
    {
        var root = NewTempRoot();
        const string block = "【任务方向】提升执行性能, 降低内存使用 (无产物引用)";

        var outp = RecallRealityGate.Verify(block, root);

        Assert.Equal(block, outp);
        Assert.DoesNotContain(RecallRealityGate.OkTag, outp, StringComparison.Ordinal);
    }

    [Fact]
    public void Verify_NoRoot_FailSafe_ReturnsOriginal()
    {
        const string block = "【已完成】stats.txt=chars=14";
        Assert.Equal(block, RecallRealityGate.Verify(block, null));
        Assert.Equal(block, RecallRealityGate.Verify(block, ""));
        Assert.Equal(block, RecallRealityGate.Verify(block, Path.Combine(Path.GetTempPath(), "r462-does-not-exist-" + Guid.NewGuid().ToString("N")[..8])));
    }

    [Fact]
    public void Verify_TraversalToken_RejectedWithoutProbe()
    {
        var root = NewTempRoot();
        var outp = RecallRealityGate.Verify("【已完成】../etc/hosts 已写入", root);
        Assert.Contains("越界路径", outp, StringComparison.Ordinal);
    }

    [Fact]
    public void Verify_Idempotent_NoDoubleTagging()
    {
        var root = NewTempRoot();
        var once = RecallRealityGate.Verify("【已完成】stats.txt=chars=14", root);
        var twice = RecallRealityGate.Verify(once, root);
        Assert.Equal(once, twice);
    }

    [Fact]
    public void Verify_MultiClause_TagsEachClauseWithPath()
    {
        var root = NewTempRoot();
        File.WriteAllText(Path.Combine(root, "count.txt"), "4\n", new UTF8Encoding(false));
        var outp = RecallRealityGate.Verify("count.txt=4; merged.txt=三行", root);
        Assert.Contains(RecallRealityGate.OkTag, outp, StringComparison.Ordinal);   // count.txt 存在
        Assert.Contains(RecallRealityGate.BadTag, outp, StringComparison.Ordinal);  // merged.txt 缺失
    }

    [Fact]
    public void Verify_FailOnly_ConsistentClaim_ZeroByteInjection()
    {
        var root = NewTempRoot();
        File.WriteAllText(Path.Combine(root, "notes.md"), "note\n", new UTF8Encoding(false));
        var block = "notes.md 已记录三行合并结论";

        var outp = RecallRealityGate.Verify(block, root, failOnly: true);

        Assert.Equal(block, outp);                       // 一致 ⇒ 一字节不注入 (token 预算)
        Assert.DoesNotContain(RecallRealityGate.OkTag, outp, StringComparison.Ordinal);
        Assert.DoesNotContain(RecallRealityGate.BadTag, outp, StringComparison.Ordinal);
    }

    [Fact]
    public void Verify_FailOnly_StaleClaim_TaggedBad()
    {
        var root = NewTempRoot();
        var block = "[工作区文件 notes.md]\nstats.txt=chars=14 已完成";

        var outp = RecallRealityGate.Verify(block, root, failOnly: true);

        Assert.Contains(RecallRealityGate.BadTag, outp, StringComparison.Ordinal);
        Assert.Contains("stats.txt", outp, StringComparison.Ordinal);
        Assert.DoesNotContain(RecallRealityGate.OkTag, outp, StringComparison.Ordinal);
    }

    // ---------- 面 2: 路径结构判定 (零后缀白名单) ----------

    [Theory]
    [InlineData("stats.txt", true)]
    [InlineData("out/merged.data", true)]
    [InlineData("a1.b2.c3", true)]
    [InlineData("1.5", false)]        // 纯数字非路径
    [InlineData("提升3.2倍", false)]   // 自然语言数字
    [InlineData("..", false)]
    [InlineData("", false)]
    public void IsPathLike_Structural_NoSuffixWhitelist(string token, bool expected)
    {
        Assert.Equal(expected, RecallRealityGate.IsPathLike(token));
    }

    [Fact]
    public void RecallRealityGate_Source_HasNoLanguageSuffixLiteral()
    {
        // 语言无关令 (R447): 闸的判定源码不得出现语言特定后缀字面量 (标签集取自数据文件)。
        var src = File.ReadAllText(Path.Combine(RepoRoot(), "src", "agent.core", "core", "RecallRealityGate.cs"), Encoding.UTF8);
        foreach (var tag in LanguageTags())
            Assert.DoesNotContain("\"" + tag + "\"", src, StringComparison.Ordinal);
    }

    // ---------- 面 3: 语言无关文本探针 ----------

    [Fact]
    public void TextProbe_BinaryAndEmptyRejected_TextAccepted()
    {
        var root = NewTempRoot();
        var text = Path.Combine(root, "logic.unit");
        File.WriteAllText(text, "if x then y\n", new UTF8Encoding(false));
        var empty = Path.Combine(root, "empty.unit");
        File.WriteAllBytes(empty, Array.Empty<byte>());
        var binary = Path.Combine(root, "blob.unit");
        File.WriteAllBytes(binary, new byte[] { 1, 0, 2, 3, 4, 5, 6, 7 });

        Assert.True(WorkspaceTextProbe.IsUsableTextFile(text));
        Assert.False(WorkspaceTextProbe.IsUsableTextFile(empty));
        Assert.False(WorkspaceTextProbe.IsUsableTextFile(binary));
    }

    [Fact]
    public void TextProbe_SuffixAllowlistOnlyWhenConfigured()
    {
        var root = NewTempRoot();
        var f = Path.Combine(root, "logic.unit");
        File.WriteAllText(f, "x\n", new UTF8Encoding(false));

        Environment.SetEnvironmentVariable(WorkspaceTextProbe.AllowlistEnv, null);
        Assert.True(WorkspaceTextProbe.SuffixAllowed(f));   // 未配置 ⇒ 全允许 (语言无关)

        Environment.SetEnvironmentVariable(WorkspaceTextProbe.AllowlistEnv, ".dead");
        Assert.False(WorkspaceTextProbe.SuffixAllowed(f));
        Environment.SetEnvironmentVariable(WorkspaceTextProbe.AllowlistEnv, ".unit, .dead");
        Assert.True(WorkspaceTextProbe.SuffixAllowed(f));

        Environment.SetEnvironmentVariable(WorkspaceTextProbe.AllowlistEnv, null);
    }

    [Fact]
    public void TextProbe_ContextAssemblerPipeline_HasNoSuffixWhitelistLiteral()
    {
        // 真缺陷回归锁 (R462): 工作区召回不得再逐字列语言后缀 (标签集取自数据文件)。
        var src = File.ReadAllText(Path.Combine(RepoRoot(), "src", "agent", "contextassembler", "ContextAssembler.cs"), Encoding.UTF8);
        Assert.DoesNotContain("var extensions = new[]", src, StringComparison.Ordinal);
        foreach (var tag in LanguageTags())
            Assert.DoesNotContain("\"" + tag + "\"", src, StringComparison.Ordinal);
    }
}
