using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using agent.core;
using agent.modelqueue;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// R495: 本地决策台账 (落盘面 + 挂载面 + 核对码确定性) 的判据表。
/// 判据只吃**结构量**: 挂载文本的常量头 / n / 码形状 / 消息列表位置 / 台账文件字节 —— 无任何用户话术特征。
/// 一致性铁律 (三源同码): 内存态 ⇒ 挂载文本 ⇒ 落盘文件行, 同一 n 的 code 必须逐字符相同。
/// </summary>
public sealed class R495LocalDecisionMountTests
{
    private static Prompt BasePrompt(string? session = "r495-session") => new()
    {
        SystemPrompt = "SYS",
        ContextPrompt = "CTX",
        UserMessage = "USER",
        SessionId = session,
        TurnIndex = 3,
        History =
        {
            new PromptMessage { Role = MessageRole.User, Content = "h-u1" },
            new PromptMessage { Role = MessageRole.Assistant, Content = "h-a1" },
        },
    };

    private sealed class EnvScope : IDisposable
    {
        private readonly string? _prevMount;
        private readonly string? _prevPath;

        public EnvScope(bool mountOn, string? ledgerPath)
        {
            _prevMount = Environment.GetEnvironmentVariable(LocalDecisionLedger.MountEnvName);
            _prevPath = Environment.GetEnvironmentVariable(LocalDecisionLedger.PathEnvName);
            Environment.SetEnvironmentVariable(LocalDecisionLedger.MountEnvName, mountOn ? "1" : null);
            Environment.SetEnvironmentVariable(LocalDecisionLedger.PathEnvName, ledgerPath);
            LocalDecisionLedger.ResetForTests();
        }

        public void Dispose()
        {
            Environment.SetEnvironmentVariable(LocalDecisionLedger.MountEnvName, _prevMount);
            Environment.SetEnvironmentVariable(LocalDecisionLedger.PathEnvName, _prevPath);
            LocalDecisionLedger.ResetForTests();
        }
    }

    // ── ① 挂载关 ⇒ 零增量 ─────────────────────────────────────────────────────

    [Fact]
    public void MountOff_AddsZeroBytes()
    {
        using var scope = new EnvScope(false, null);
        LocalDecisionLedger.Record("r495-session", 1, "pass", "raw");
        var qp = ModelQueueAdapter.ToQueuePrompt(BasePrompt(), false, false);
        Assert.False(qp.Mount.On);
        var msgs = ModelQueueRouter.BuildMessages(qp);
        Assert.Equal(5, msgs.Count);                       // system / context / history×2 / user
        Assert.Equal("user", msgs[^1].Role);
        Assert.DoesNotContain(msgs, m => m.Content.Contains(LocalDecisionLedger.MountHeader, StringComparison.Ordinal));
        Assert.Equal(scope is not null, true);
    }

    // ── ② 挂载开 ⇒ 只在尾部追加 (前缀逐字节不变) ───────────────────────────────

    [Fact]
    public void MountOn_AppendsTailOnly_PrefixBitForBitSame()
    {
        using var scope = new EnvScope(true, null);
        _ = scope;
        LocalDecisionLedger.Record("r495-session", 1, "pass", "raw-1");
        LocalDecisionLedger.Record("r495-session", 2, "skip", "raw-2");

        var onQp = ModelQueueAdapter.ToQueuePrompt(BasePrompt(), false, true);
        var offQp = ModelQueueAdapter.ToQueuePrompt(BasePrompt(), false, false);
        Assert.True(onQp.Mount.On);
        Assert.False(offQp.Mount.On);

        var on = ModelQueueRouter.BuildMessages(onQp);
        var off = ModelQueueRouter.BuildMessages(offQp);
        Assert.Equal(off.Count + 1, on.Count);
        for (var i = 0; i < off.Count; i++)
        {
            Assert.Equal(off[i].Role, on[i].Role);
            Assert.Equal(off[i].Content, on[i].Content);
        }
        var mountMsg = on[^1];
        Assert.Equal("system", mountMsg.Role);
        Assert.StartsWith(LocalDecisionLedger.MountHeader, mountMsg.Content, StringComparison.Ordinal);
        Assert.Equal(2, onQp.Mount.N);
        Assert.Contains("code=" + onQp.Mount.Code, mountMsg.Content, StringComparison.Ordinal);
    }

    // ── ③ 核对码: 进程内确定 + 幂等 (R496: 可复算性已**移除**, 见 R496NonRecomputableTests) ─────

    [Fact]
    public void CheckCode_DeterministicInProcess_Idempotent()
    {
        using var scope = new EnvScope(true, null);
        _ = scope;
        LocalDecisionLedger.Record("s1", 1, "pass", "aaaaaaaaaa");
        LocalDecisionLedger.Record("s1", 2, "skip", "bbbb");
        LocalDecisionLedger.Record("s1", 3, "pass", "ccccccc");

        var code = LocalDecisionLedger.CheckCode("s1");
        Assert.StartsWith(LocalDecisionLedger.CodePrefix, code, StringComparison.Ordinal);
        Assert.Equal(LocalDecisionLedger.CodeHexLen, code.Length - LocalDecisionLedger.CodePrefix.Length);
        Assert.True(code[(LocalDecisionLedger.CodePrefix.Length)..]
            .All(c => (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')));

        var rows = new List<string>
        {
            LocalDecisionLedger.Canon(1, "pass", "aaaaaaaaaa".Length),
            LocalDecisionLedger.Canon(2, "skip", "bbbb".Length),
            LocalDecisionLedger.Canon(3, "pass", "ccccccc".Length),
        };
        Assert.Equal(code, LocalDecisionLedger.CodeOf("s1", rows));
        Assert.NotEqual(code, LocalDecisionLedger.CheckCode("s1", 2));   // 码随台账增长, 非常量

        LocalDecisionLedger.Record("s1", 3, "pass", "ccccccc");          // 幂等: 同 (turn,kind,chars)
        Assert.Equal(code, LocalDecisionLedger.CheckCode("s1"));
        Assert.Equal(3, LocalDecisionLedger.Count("s1"));
    }

    // ── ④ 三源同码: 内存 / 落盘文件行 / 挂载文本 ──────────────────────────────

    [Fact]
    public void LedgerFile_ThreeSourcesAgree_SameCode()
    {
        var path = Path.Combine(Path.GetTempPath(), "r495-ledger-" + Guid.NewGuid().ToString("N") + ".jsonl");
        using var scope = new EnvScope(true, path);
        _ = scope;
        try
        {
            LocalDecisionLedger.Record("s2", 1, "pass", "raw-1");
            LocalDecisionLedger.Record("s2", 2, "skip", "ra\"w\n2");
            var mount = LocalDecisionLedger.RenderMount("s2");

            var lines = File.ReadAllLines(path, Encoding.UTF8);
            Assert.Equal(2, lines.Length);
            Assert.Equal(2, mount.N);
            var rows = new List<string>();
            for (var i = 0; i < lines.Length; i++)
            {
                var o = JsonDocument.Parse(lines[i]).RootElement;
                Assert.Equal(i + 1, o.GetProperty("n").GetInt32());
                Assert.Equal("s2", o.GetProperty("session").GetString());
                Assert.Equal(i + 1, o.GetProperty("turn").GetInt32());
                rows.Add(o.GetProperty("canon").GetString()!);
                // R496: 落盘面只留**指纹** (code8/key_id) —— 逐行核「声明的指纹 == 前 i+1 条规范行复算码的指纹」
                Assert.Equal(LocalDecisionLedger.Code8(LocalDecisionLedger.CodeOf("s2", rows)), o.GetProperty("code8").GetString());
                Assert.False(o.TryGetProperty("code", out _));                     // 真值字段已不再落盘
                Assert.DoesNotContain(LocalDecisionLedger.CodePrefix, lines[i], StringComparison.Ordinal);
                Assert.Equal(8, o.GetProperty("key_id").GetString()!.Length);
            }
            Assert.Equal(LocalDecisionLedger.Code8(LocalDecisionLedger.CheckCode("s2")),
                JsonDocument.Parse(lines[^1]).RootElement.GetProperty("code8").GetString());
            Assert.Equal(mount.Code, LocalDecisionLedger.CheckCode("s2"));
            Assert.Equal(2, LocalDecisionLedger.FileWrites);
            Assert.Equal(0, LocalDecisionLedger.FileErrors);
            Assert.NotEqual(0xEF, File.ReadAllBytes(path)[0]);           // 去 BOM 铁律
            Assert.Equal(2, LocalDecisionLedger.Recorded);
        }
        finally
        {
            if (File.Exists(path)) File.Delete(path);
        }
    }

    // ── ⑤ 轴关 / 无会话 ⇒ 零字节 (旧行为面无回归) ─────────────────────────────

    [Fact]
    public void AxisOff_Or_NoSession_ProducesOff()
    {
        using var off = new EnvScope(false, null);
        _ = off;
        LocalDecisionLedger.Record("s3", 1, "pass", "x");
        Assert.False(LocalDecisionLedger.RenderMount("s3").On);

        using var on = new EnvScope(true, null);
        _ = on;
        LocalDecisionLedger.Record("s3", 1, "pass", "x");
        Assert.False(LocalDecisionLedger.RenderMount(null).On);
        Assert.False(LocalDecisionLedger.RenderMount(string.Empty).On);
        Assert.False(LocalDecisionLedger.RenderMount("   ").On);
        Assert.Equal(string.Empty, LocalDecisionLedger.Record(null, 1, "pass", "x"));   // 无会话不记账
        Assert.Equal(1, LocalDecisionLedger.Count("s3"));
    }

    // ── ⑥ 动作环 Clone 必透传挂载块 (否则环内第 2 次远端调用丢挂载) ─────────────

    [Fact]
    public void ActionLoopClone_PropagatesMount()
    {
        using var scope = new EnvScope(true, null);
        _ = scope;
        LocalDecisionLedger.Record("s4", 1, "pass", "x");
        var qp = ModelQueueAdapter.ToQueuePrompt(BasePrompt("s4"), false, true);
        var clone = ActionLoopRunner.Clone(qp, new List<QueuePostUserMessage>());
        Assert.Equal(qp.Mount.Code, clone.Mount.Code);
        Assert.Equal(qp.Mount.N, clone.Mount.N);
        Assert.Equal(qp.Mount.Text, clone.Mount.Text);
        Assert.Contains(ModelQueueRouter.BuildMessages(clone),
            m => m.Content.Contains(LocalDecisionLedger.MountHeader, StringComparison.Ordinal));
    }

    // ── ⑦ 挂载文本形状: 常量头 + 结构量 (无用户文本) ────────────────────────────

    [Fact]
    public void MountText_ShapeIsConstantHeaderPlusNumbers()
    {
        using var scope = new EnvScope(true, null);
        _ = scope;
        LocalDecisionLedger.Record("s5", 7, "skip", "basis-basis");
        var m = LocalDecisionLedger.RenderMount("s5");
        var lines = m.Text.Split('\n');
        Assert.StartsWith(LocalDecisionLedger.MountHeader, lines[0], StringComparison.Ordinal);
        Assert.Contains("session=" + LocalDecisionLedger.Sha8("s5"), lines[0], StringComparison.Ordinal);
        Assert.Contains("n=1", lines[0], StringComparison.Ordinal);
        Assert.Contains("code=" + LocalDecisionLedger.CodePrefix, lines[0], StringComparison.Ordinal);
        Assert.Contains(LocalDecisionLedger.Canon(7, "skip", "basis-basis".Length), m.Text, StringComparison.Ordinal);
        Assert.True(m.Text.Length < 512);
        Assert.True(LocalDecisionLedger.MountEnvName.Length > 0);
    }
}
