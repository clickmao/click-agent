using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.action;
using agent.core;
using agent.modelqueue;
using Xunit;
namespace agent.tests;

/// <summary>
/// R496 判据表 (四个候选各一面 + 一个收口面), 全部只吃**结构量**:
///   ① 挂载真值不可复算: 旧公开配方 (sha256) 不再等于真值; 真值随密钥变; 落盘/文本面无真值;
///   ② 挂载文本显式授权复述 (R495 反向诊断: 旧文案被读成金丝雀 ⇒ 治疗向回答全红);
///   ③-a 命令面越界收口: 引用工作区外路径的命令**不执行且不回显正文** (`2>/dev/null` 等惯用法不受影响);
///   ③-b 回灌面越界子句只留标记 + 路径 token (正文隐去);
///   ⑦ 打点面与实发面同源 (由 R496 面判据器读真实遥测核, 这里只锁常量/指纹函数)。
/// </summary>
public sealed class R496NonRecomputableTests
{
    private static readonly byte[] KeyA = Enumerable32(7);
    private static readonly byte[] KeyB = Enumerable32(9);

    private static byte[] Enumerable32(byte seed)
    {
        var b = new byte[32];
        for (var i = 0; i < b.Length; i++) b[i] = (byte)(seed + i);
        return b;
    }

    private static List<string> Rows() => new()
    {
        LocalDecisionLedger.Canon(1, "pass", 4),
        LocalDecisionLedger.Canon(2, "skip", 6),
    };

    // ── ① 真值不可复算 ────────────────────────────────────────────────────────

    [Fact]
    public void Code_NotRecomputableByPublicRecipe()
    {
        LocalDecisionLedger.SetKeyForTests(KeyA);
        var rows = Rows();
        var code = LocalDecisionLedger.CodeOf("s-496", rows);

        // R495 的公开配方 (无密钥 sha256) —— 任何人拿到 ledger 的 canon 行都能算; R496 后必须**不再成立**。
        var body = LocalDecisionLedger.Compose("s-496", rows);
        var oldRecipe = LocalDecisionLedger.CodePrefix
            + Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(body))).ToLowerInvariant()[..LocalDecisionLedger.CodeHexLen];
        Assert.NotEqual(oldRecipe, code);
        Assert.Equal(LocalDecisionLedger.CodePrefix.Length + LocalDecisionLedger.CodeHexLen, code.Length);
    }

    [Fact]
    public void Code_KeyDependent_SameInputDifferentKeyDifferentCode()
    {
        var rows = Rows();
        LocalDecisionLedger.SetKeyForTests(KeyA);
        var a = LocalDecisionLedger.CodeOf("s-496", rows);
        LocalDecisionLedger.SetKeyForTests(KeyB);
        var b = LocalDecisionLedger.CodeOf("s-496", rows);
        LocalDecisionLedger.SetKeyForTests(KeyA);
        Assert.NotEqual(a, b);
        Assert.Equal(a, LocalDecisionLedger.CodeOf("s-496", rows));   // 同密钥 ⇒ 进程内确定 (判据器可核指纹)
    }

    [Fact]
    public void Fingerprints_DoNotContainTruth()
    {
        LocalDecisionLedger.SetKeyForTests(KeyA);
        var code = LocalDecisionLedger.CodeOf("s-496", Rows());
        var code8 = LocalDecisionLedger.Code8(code);
        Assert.Equal(8, code8.Length);
        Assert.DoesNotContain(LocalDecisionLedger.CodePrefix, code8, StringComparison.Ordinal);
        Assert.DoesNotContain(code[LocalDecisionLedger.CodePrefix.Length..], code8, StringComparison.Ordinal);
        var keyId = LocalDecisionLedger.KeyId();
        Assert.Equal(8, keyId.Length);
        Assert.DoesNotContain(Convert.ToHexString(KeyA).ToLowerInvariant(), keyId, StringComparison.Ordinal);
    }

    [Fact]
    public void LedgerFile_NoTruthBytes_OnlyFingerprints()
    {
        var path = Path.Combine(Path.GetTempPath(), "r496-ledger-" + Guid.NewGuid().ToString("N") + ".jsonl");
        var prevMount = Environment.GetEnvironmentVariable(LocalDecisionLedger.MountEnvName);
        var prevPath = Environment.GetEnvironmentVariable(LocalDecisionLedger.PathEnvName);
        try
        {
            LocalDecisionLedger.SetKeyForTests(KeyA);
            Environment.SetEnvironmentVariable(LocalDecisionLedger.MountEnvName, "1");
            Environment.SetEnvironmentVariable(LocalDecisionLedger.PathEnvName, path);
            LocalDecisionLedger.ResetForTests();
            LocalDecisionLedger.Record("s-496", 1, "pass", "raw-1");
            LocalDecisionLedger.Record("s-496", 2, "skip", "raw-2");
            var mount = LocalDecisionLedger.RenderMount("s-496");

            var text = File.ReadAllText(path, Encoding.UTF8);
            Assert.DoesNotContain(mount.Code, text, StringComparison.Ordinal);          // 真值不落盘 (R495 泄漏通道)
            Assert.DoesNotContain(LocalDecisionLedger.CodePrefix, text, StringComparison.Ordinal);
            Assert.Contains(LocalDecisionLedger.Code8(mount.Code), text, StringComparison.Ordinal);
            Assert.Equal(2, LocalDecisionLedger.FileWrites);
        }
        finally
        {
            Environment.SetEnvironmentVariable(LocalDecisionLedger.MountEnvName, prevMount);
            Environment.SetEnvironmentVariable(LocalDecisionLedger.PathEnvName, prevPath);
            LocalDecisionLedger.ResetForTests();
            LocalDecisionLedger.SetKeyForTests(KeyA);
            if (File.Exists(path)) File.Delete(path);
        }
    }

    // ── ② 挂载文本显式授权复述 ────────────────────────────────────────────────

    [Fact]
    public void MountText_ExplicitlyAuthorizesRestating()
    {
        var prevMount = Environment.GetEnvironmentVariable(LocalDecisionLedger.MountEnvName);
        try
        {
            LocalDecisionLedger.SetKeyForTests(KeyA);
            Environment.SetEnvironmentVariable(LocalDecisionLedger.MountEnvName, "1");
            LocalDecisionLedger.ResetForTests();
            LocalDecisionLedger.Record("s-496", 1, "pass", "raw-1");
            var mount = LocalDecisionLedger.RenderMount("s-496");

            Assert.Contains("直接复述", mount.Text, StringComparison.Ordinal);
            Assert.DoesNotContain("无法从别处得到", mount.Text, StringComparison.Ordinal);  // R495 金丝雀误读源
            Assert.Contains("code=" + mount.Code, mount.Text, StringComparison.Ordinal);
            Assert.Contains("n=" + mount.N, mount.Text, StringComparison.Ordinal);
        }
        finally
        {
            Environment.SetEnvironmentVariable(LocalDecisionLedger.MountEnvName, prevMount);
            LocalDecisionLedger.ResetForTests();
            LocalDecisionLedger.SetKeyForTests(KeyA);
        }
    }

    // ── ③-a 命令面越界收口 ───────────────────────────────────────────────────

    [Theory]
    [InlineData("grep -rIn LCM- /home/agentuser/AgentFramework/src", "/home/agentuser/AgentFramework/src")]  // 字面绝对路径越界
    [InlineData("cat ../outside.txt", "../outside.txt")]                                                     // .. 上跳
    [InlineData("ls ~/secrets", "~/secrets")]                                                                // 家目录
    [InlineData("cat /etc/hostname", "/etc/hostname")]
    public void Command_OutOfRootToken_Detected(string command, string expectToken)
    {
        var root = NewTempDir();
        try
        {
            Assert.Equal(expectToken, WorkspaceActionPort.FindOutOfRootToken(command, root));
        }
        finally { Directory.Delete(root, true); }
    }

    [Fact]
    public void Command_InRootOrDeviceIdioms_NotFlagged()
    {
        var root = NewTempDir();
        try
        {
            Assert.Null(WorkspaceActionPort.FindOutOfRootToken("find . -name \"*.json\" 2>/dev/null", root));
            Assert.Null(WorkspaceActionPort.FindOutOfRootToken("ls -la " + root + "/data", root));
            Assert.Null(WorkspaceActionPort.FindOutOfRootToken("echo hi; cat data/out.json | head -20", root));
            Assert.Null(WorkspaceActionPort.FindOutOfRootToken("pwd", root));
        }
        finally { Directory.Delete(root, true); }
    }

    [Fact]
    public async Task Command_OutOfRoot_NotExecuted_NoEcho()
    {
        var root = NewTempDir();
        try
        {
            var port = new WorkspaceActionPort(root);
            var r = await port.ExecuteAsync(new ActionToolCall
            {
                Name = "run_command",
                ArgumentsJson = "{\"command\":\"cat /etc/hostname; echo CANARY_R496\"}",
            }, CancellationToken.None);
            Assert.False(r.Ok);
            Assert.Equal(WorkspaceActionPort.BoundaryRefusedExitCode, r.ExitCode);
            Assert.Contains("越界", r.Output, StringComparison.Ordinal);
            Assert.DoesNotContain("CANARY_R496", r.Output, StringComparison.Ordinal);   // 未执行 ⇒ 无回显
            var host = File.Exists("/etc/hostname") ? File.ReadAllText("/etc/hostname").Trim() : string.Empty;
            if (host.Length > 0) Assert.DoesNotContain(host, r.Output, StringComparison.Ordinal);
            // 工作区内的命令照跑
            var ok = await port.ExecuteAsync(new ActionToolCall
            {
                Name = "run_command",
                ArgumentsJson = "{\"command\":\"echo CANARY_R496 2>/dev/null\"}",
            }, CancellationToken.None);
            Assert.True(ok.Ok, ok.Output);
            Assert.Contains("CANARY_R496", ok.Output, StringComparison.Ordinal);
        }
        finally { Directory.Delete(root, true); }
    }

    // ── ③-b 回灌面越界子句正文隐去 ───────────────────────────────────────────

    [Fact]
    public void RecallGate_OutOfRootClause_Redacted_ButInRootEchoPreserved()
    {
        var root = NewTempDir();
        try
        {
            var leak = RecallRealityGate.Verify("stats.txt=14;[工作区文件] /home/agentuser/AgentFramework/src/agent.modelqueue/LocalDecisionLedger.cs:16 泄漏行", root);
            Assert.Contains(RecallRealityGate.RedactMarker, leak, StringComparison.Ordinal);
            Assert.Contains("越界路径", leak, StringComparison.Ordinal);
            Assert.DoesNotContain("泄漏行", leak, StringComparison.Ordinal);              // 越界 ⇒ 正文不回显
            Assert.DoesNotContain("LocalDecisionLedger.cs:16 泄漏行", leak, StringComparison.Ordinal);

            // 工作区内缺失文件: 正文仍原样回收 + 标签 (旧契约逐字节不变)
            var stale = RecallRealityGate.Verify("absent.txt=3", root);
            Assert.Contains("absent.txt", stale, StringComparison.Ordinal);
            Assert.Contains(RecallRealityGate.BadTag, stale, StringComparison.Ordinal);
        }
        finally { Directory.Delete(root, true); }
    }

    private static string NewTempDir()
    {
        var d = Path.Combine(Path.GetTempPath(), "r496-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(d);
        return d;
    }
}
