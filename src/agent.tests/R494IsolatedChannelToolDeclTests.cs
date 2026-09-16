using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using agent.core;
using agent.intent;
using agent.modelqueue;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// R494: 声明面**通道轴** (隔离通道恒不下发工作区工具) 的判据表 + 透传锁 + 调用点标记锁。
/// 依据: `eval/rover/r493/calls-*.jsonl` —— 隔离通道 (`[微步骤隔离问询]` / 一次性隔离子任务) 因意图键为空
/// 命中 R490 意图轴的「未知意图保守下发」分支 ⇒ B 臂 4/9 空正文调用全部来自该通道 (上游对幻觉路径反复
/// list/read, 通道 7,305 tok / 该臂 7.22%); T 臂 (意图轴开) 仍 1/1 该通道带 tools。
/// 判据只吃**调用点显式置位的结构量** (Prompt.IsolatedChannel), 不引入任何文本特征。
/// </summary>
public sealed class R494IsolatedChannelToolDeclTests
{
    private static IEnumerable<string?> Intents()
    {
        yield return null;
        yield return "";
        yield return "   ";
        foreach (var i in IntentRecognizer.KnownIntents) yield return i;
        yield return "unheard_of_intent";
    }

    // ── 通道轴: 关 ⇒ 与 R490 意图轴逐位相同 (零回归面) ─────────────────────────

    [Fact]
    public void ChannelGateOff_LegacyDecisionsPreserved_BitForBit()
    {
        foreach (var intent in Intents())
            foreach (var gate in new[] { false, true })
                foreach (var isolated in new[] { false, true })
                {
                    var legacy = ToolDeclGate.ShouldDeclare(intent, gate);
                    Assert.Equal(legacy, ToolDeclGate.ShouldDeclare(intent, gate, isolated, channelGateEnabled: false));
                    Assert.Equal(ToolDeclGate.DecideReason(intent, gate),
                        ToolDeclGate.DecideReason(intent, gate, isolated, channelGateEnabled: false));
                }
    }

    // ── 通道轴: 开 + 隔离 ⇒ 恒不下发 (含工具类意图 —— 通道结构上就没有工作区) ──

    [Fact]
    public void ChannelGateOn_IsolatedChannel_NeverDeclares()
    {
        foreach (var intent in Intents())
            foreach (var gate in new[] { false, true })
            {
                Assert.False(ToolDeclGate.ShouldDeclare(intent, gate, isolatedChannel: true, channelGateEnabled: true));
                Assert.Equal("isolated_channel_drop",
                    ToolDeclGate.DecideReason(intent, gate, isolatedChannel: true, channelGateEnabled: true));
            }
        // 工具类意图也必须丢 (通道轴优先于意图轴: 隔离通道里的「改文件」是幻觉动作, R493 实测 `d data`)
        foreach (var t in ToolDeclGate.ToolIntents)
            Assert.False(ToolDeclGate.ShouldDeclare(t, gateEnabled: false, isolatedChannel: true, channelGateEnabled: true));
    }

    // ── 通道轴: 开 + 非隔离 ⇒ 退回意图轴 (主链能力不受影响) ────────────────────

    [Fact]
    public void ChannelGateOn_MainChain_UsesIntentAxisOnly()
    {
        foreach (var intent in Intents())
            foreach (var gate in new[] { false, true })
            {
                Assert.Equal(ToolDeclGate.ShouldDeclare(intent, gate),
                    ToolDeclGate.ShouldDeclare(intent, gate, isolatedChannel: false, channelGateEnabled: true));
                Assert.Equal(ToolDeclGate.DecideReason(intent, gate),
                    ToolDeclGate.DecideReason(intent, gate, isolatedChannel: false, channelGateEnabled: true));
            }
        // 主链的三个能力锚点不得被通道轴误伤
        foreach (var t in ToolDeclGate.ToolIntents)
            Assert.True(ToolDeclGate.ShouldDeclare(t, gateEnabled: true, isolatedChannel: false, channelGateEnabled: true));
        Assert.True(ToolDeclGate.ShouldDeclare(null, gateEnabled: true, isolatedChannel: false, channelGateEnabled: true));
    }

    [Fact]
    public void ChannelGate_EnvSwitch_DefaultOff_AndIndependentFromIntentGate()
    {
        var savedCh = Environment.GetEnvironmentVariable(ToolDeclGate.ChannelEnvName);
        var savedGate = Environment.GetEnvironmentVariable(ToolDeclGate.EnvName);
        try
        {
            Environment.SetEnvironmentVariable(ToolDeclGate.ChannelEnvName, null);
            Assert.False(ToolDeclGate.IsChannelGateEnabled());           // 未设 = 关 (生产行为不变)
            Environment.SetEnvironmentVariable(ToolDeclGate.ChannelEnvName, "off");
            Assert.False(ToolDeclGate.IsChannelGateEnabled());
            Environment.SetEnvironmentVariable(ToolDeclGate.ChannelEnvName, "0");
            Assert.False(ToolDeclGate.IsChannelGateEnabled());
            Environment.SetEnvironmentVariable(ToolDeclGate.ChannelEnvName, "false");
            Assert.False(ToolDeclGate.IsChannelGateEnabled());
            Environment.SetEnvironmentVariable(ToolDeclGate.ChannelEnvName, "on");
            Assert.True(ToolDeclGate.IsChannelGateEnabled());
            // 分轴: 通道轴开不得把意图轴也打开 (反之亦然) —— 单变量消融的前提
            Environment.SetEnvironmentVariable(ToolDeclGate.EnvName, null);
            Assert.False(ToolDeclGate.IsEnabled());
        }
        finally
        {
            Environment.SetEnvironmentVariable(ToolDeclGate.ChannelEnvName, savedCh);
            Environment.SetEnvironmentVariable(ToolDeclGate.EnvName, savedGate);
        }
    }

    // ── 透传锁: Prompt → QueuePrompt (声明面唯一输入) ─────────────────────────

    [Fact]
    public void ToQueuePrompt_PropagatesIsolatedChannel()
    {
        var iso = new Prompt { SystemPrompt = "s", UserMessage = "u", IsolatedChannel = true };
        var main = new Prompt { SystemPrompt = "s", UserMessage = "u" };
        Assert.True(ModelQueueAdapter.ToQueuePrompt(iso).IsolatedChannel);
        Assert.False(ModelQueueAdapter.ToQueuePrompt(main).IsolatedChannel);   // 默认 false = 主链
    }

    // ── 透传锁: 动作环 Clone (R490 同一类缺陷: 判据随 Clone 丢失) ─────────────

    [Fact]
    public void ActionLoopClone_PropagatesIsolatedChannel()
    {
        var qp = ModelQueueAdapter.ToQueuePrompt(new Prompt { SystemPrompt = "s", UserMessage = "u", IsolatedChannel = true });
        var clone = ActionLoopRunner.Clone(qp, new List<QueuePostUserMessage>());
        Assert.True(clone.IsolatedChannel);
        qp.IsolatedChannel = false;
        Assert.False(ActionLoopRunner.Clone(qp, new List<QueuePostUserMessage>()).IsolatedChannel);
    }

    // ── 请求字节面: 通道轴开 + 隔离 ⇒ 请求体里没有 tools 键 ───────────────────

    [Fact]
    public void IsolatedChannelRequest_CarriesNoToolsKey()
    {
        var p = new Prompt { SystemPrompt = "s", UserMessage = "微问题", IsolatedChannel = true };
        var chOn = true;
        var declared = ToolDeclGate.ShouldDeclare(p.Intent, ToolDeclGate.IsEnabled(), p.IsolatedChannel, chOn);
        var toolsJson = declared ? ActionToolSpec.ChatToolsJson : null;
        var body = ModelQueueRouter.SerializeChatRequest(new QueueChatRequest
        {
            Model = "deepseek-flash",
            Messages = ModelQueueRouter.BuildMessages(ModelQueueAdapter.ToQueuePrompt(p)),
            ToolsJson = toolsJson,
        });
        Assert.DoesNotContain("\"tools\"", body, StringComparison.Ordinal);
    }

    // ── 调用点标记锁 (源码面): 隔离通道必须显式置位, 且数量与已知通道数一致 ────

    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !Directory.Exists(Path.Combine(dir.FullName, "src", "agent")))
            dir = dir.Parent;
        Assert.NotNull(dir);
        return dir!.FullName;
    }

    /// <summary>
    /// 非**产品源**目录排除 (构建产物 + 测试工程) —— 按路径段判定。
    /// 踩过的坑: `Path.Combine("obj", Path.DirectorySeparatorChar.ToString())` 在第二段为绝对路径时
    /// 退化成 "/" ⇒ 该条件对**所有**文件成立 ⇒ 扫描集恒空 (形式上是"全绿"的假阴性)。
    /// 测试工程自带同名字面量 ⇒ 必须排除, 否则反向计数被测试自身污染。
    /// </summary>
    private static bool OutsideProductSource(string path)
        => path.Split(Path.DirectorySeparatorChar).Any(s => s == "obj" || s == "bin" || s == "agent.tests");

    private static IEnumerable<string> ProductSources(string srcDir)
        => Directory.EnumerateFiles(srcDir, "*.cs", SearchOption.AllDirectories).Where(f => !OutsideProductSource(f));

    [Fact]
    public void IsolatedCallSites_AreMarked()
    {
        var srcDir = Path.Combine(RepoRoot(), "src");
        // 结构锁 = **SystemPrompt 赋值行**命中隔离声明 (注释里的同串不算) ⇒ 每条隔离 Prompt 构造点
        // 必须在同一构造块内显式置位 IsolatedChannel = true。新增隔离通道 ⇒ 本锁变红。
        var sites = new List<(string File, int Line)>();
        foreach (var f in ProductSources(srcDir))
        {
            var lines = File.ReadAllLines(f);
            for (var i = 0; i < lines.Length; i++)
            {
                var line = lines[i];
                if (!line.Contains("SystemPrompt") || !line.Contains("=")) continue;
                if (!line.Contains("不引用任何外部会话历史") && !line.Contains("不引用任何先前的对话上下文")) continue;
                sites.Add((f, i));
            }
        }
        // 已知隔离 Prompt 构造点 = 2 (微步骤隔离问询 / 一次性隔离子任务)
        Assert.Equal(2, sites.Count);
        foreach (var (file, idx) in sites)
        {
            var lines = File.ReadAllLines(file);
            var window = string.Join('\n', lines.Skip(idx).Take(12));   // 同一构造块内 (构造字面量 ≤12 行)
            Assert.Contains("IsolatedChannel = true", window);
        }
        // 反向: 产品源恰有 2 处置位 (既不漏标也不多标)
        var marked = ProductSources(srcDir).Sum(f => File.ReadAllLines(f).Count(l => l.Contains("IsolatedChannel = true")));
        Assert.Equal(2, marked);
    }

    [Fact]
    public void R493_LeakEvidence_IsPreservedInRoundArtifacts()
    {
        // 归因可复现: 该轮真机台账里, 隔离通道的远端调用带 tools 且含空正文工具往返
        var path = Path.Combine(RepoRoot(), "eval", "rover", "r493", "calls-Aroleb.jsonl");
        if (!File.Exists(path)) return;      // 台账不在场 ⇒ 不伪造读数 (round 数据可被清理)
        var rows = File.ReadAllLines(path, System.Text.Encoding.UTF8)
            .Where(l => l.Trim().Length > 0)
            .ToList();
        Assert.NotEmpty(rows);
        var isoCalls = 0; var isoWithTools = 0;
        foreach (var l in rows)
        {
            using var d = JsonDocument.Parse(l);
            var r = d.RootElement;
            if (!r.ToString().Contains("微步骤隔离问询")) continue;
            isoCalls++;
            // tools_n 落在 sampling 子对象内 (R493 台账形状; 顶层没有该键 ⇒ 早期版本读法曾误判为 0)
            if (r.TryGetProperty("sampling", out var s) && s.TryGetProperty("tools_n", out var tn) && tn.GetInt32() > 0)
                isoWithTools++;
        }
        Assert.True(isoCalls > 0, "R493 台账应含隔离通道调用");
        Assert.Equal(isoCalls, isoWithTools);   // 泄漏形态: 该通道**全部**调用都带 tools
    }
}
