using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using agent.r1;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// R550 · 探针证据回灌的**独立预算**轴（AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR, 默认 0=关）。
///
/// 定因（R549）：题面公开用例回放（探针，非模型自述）已判定产物不合格时，那次回灌修复与
/// 「执行实测回灌」**共用**同一预算（MaxExecRepair）⇒ 二者只能行使其一：探针先到 ⇒ 执行回灌
/// 预算被挤占 ⇒ 测量到的「产物在自撰自测处未达成仍交付」无法用第二次真证据修。
///
/// 钉五件事（成对判据 = 正向 + 判别性负控 + 零回归 + 上界）：
///   ① 轴关(0) ⇒ 探针失败照旧借执行回灌预算（Calls=2, ExecRepairs=1）、台账**无** probe_repairs/prepare 字段（零回归可机检）；
///   ② 轴开(1) ⇒ 探针那次修复**不吃**执行回灌预算：同输入下轴关停在坏产物（rc=8 public_probe_unmet, Calls=2），
///      轴开则两次真证据各得其一并修到 rc=0（Calls=3, ProbeRepairs=1, ExecRepairs=1）；
///   ③ 负控：轴开但产物一次即过 ⇒ 不多要调用（Calls=1, ProbeRepairs=0）；
///   ④ 负控：无探针 ⇒ 轴 inert（ProbeRepairs=0，分类与旧路径同）；
///   ⑤ 上界：产物始终不合格 ⇒ 调用数 ≤ 1+预算(探针)+预算(执行)，不失控。
/// </summary>
public class R1ProbeRepairBudgetTests
{
    private static string NewSandbox()
    {
        var dir = Path.Combine(Path.GetTempPath(), "r1proberep-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    private static R1Options Opt(string sandbox, bool probe, int maxProbeRepair, int maxExecRepair = 1,
        int earlyStopPfail = 0) =>
        new(sandbox, 1, 60, null, null, "test", maxExecRepair, probe, earlyStopPfail, maxProbeRepair);

    private sealed class ScriptedCaller : agent.ILLMCaller
    {
        private readonly Queue<string> _replies;
        public int Calls;

        public ScriptedCaller(params string[] replies) => _replies = new Queue<string>(replies);

        public Task<agent.LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
        {
            Calls++;
            var content = _replies.Count > 0 ? _replies.Dequeue() : string.Empty;
            return Task.FromResult(new agent.LLMResponse
            {
                Content = content, Success = true,
                PromptTokens = 1000, CompletionTokens = 200,
                CacheHitTokens = 900, CacheMissTokens = 100,
            });
        }
    }

    private static string Esc(string s) =>
        s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n");

    private static string Step(string id, string path, string content) =>
        "{\"id\":\"" + id + "\",\"tool\":\"write_file\",\"args\":{\"path\":\"" + Esc(path) + "\",\"content\":\""
        + Esc(content) + "\"},\"depends_on\":[]}";

    private const string SyntheticTask =
        "用 Python 3 实现 `games/` 包, 入口 `python3 -m games <game_id>`（`<game_id>` 取 a）。\n\n"
        + "### 游戏 `a`\n输入:\n7\n期望输出:\n14\n\n请把完整程序放在一个 ```python 围栏代码块内。\n";

    private const string MainPy =
        "import sys\nfrom games import a\nsys.stdout.write({\"a\": a}[sys.argv[1]].solve(sys.stdin.read()))\n";

    private static string PlanJson(string aPy) =>
        "{\"schema_version\":\"r1.0\",\"intent\":\"code_task\",\"confidence\":0.9,\"entities\":[],\"constraints\":[],"
        + "\"missing_slots\":[],\"ambiguities\":[],\"done_when\":[],\"refusal\":null,\"plan\":["
        + Step("s1", "games/__init__.py", "")
        + "," + Step("s2", "games/__main__.py", MainPy)
        + "," + Step("s3", "games/a.py", aPy)
        + "]}";

    private const string GoodAPy = "def solve(text):\n    return str(int(text.split()[0]) * 2)\n";
    private const string BadAPy = "def solve(text):\n    return str(int(text.split()[0]) * 3)\n";

    /// <summary>① 轴关 = 旧行为（探针失败借执行回灌预算；台账无新字段）。</summary>
    [Fact]
    public async Task ProbeBudget_Off_Keeps_Old_Behavior_And_No_Ledger_Field()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller(PlanJson(BadAPy), PlanJson(GoodAPy));
            var res = await R1Pipeline.RunAsync(caller, SyntheticTask, Opt(sb, probe: true, maxProbeRepair: 0),
                CancellationToken.None);

            Assert.Equal(0, res.Rc);
            Assert.Equal("done", res.Stage);
            Assert.Equal(2, caller.Calls);
            Assert.Equal(1, res.Stats.ExecRepairs);
            Assert.Equal(0, res.ProbeRepairs);
            Assert.DoesNotContain("probe_repairs", R1Transcript.Marker(res), StringComparison.Ordinal);
            var render = R1Transcript.Render(res, Opt(sb, true, 0), SyntheticTask);
            Assert.DoesNotContain("probe_repairs", render, StringComparison.Ordinal);
            Assert.DoesNotContain("probe_repair_budget", render, StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    /// <summary>② 轴开 ⇒ 探针修复不吃执行回灌预算：两次真证据各得其一, 修到 rc=0。</summary>
    [Fact]
    public async Task ProbeBudget_On_Frees_The_Exec_Budget_And_Reaches_Done()
    {
        var sb = NewSandbox();
        try
        {
            // 三包：探针修复(1) → 执行回灌(1) → 收口。轴关时第 3 次调用根本不会发生。
            var caller = new ScriptedCaller(PlanJson(BadAPy), PlanJson(BadAPy), PlanJson(GoodAPy));
            var res = await R1Pipeline.RunAsync(caller, SyntheticTask, Opt(sb, probe: true, maxProbeRepair: 1),
                CancellationToken.None);

            Assert.Equal(0, res.Rc);
            Assert.Equal("done", res.Stage);
            Assert.Equal(3, caller.Calls);
            Assert.Equal(1, res.ProbeRepairs);
            Assert.Equal(1, res.Stats.ExecRepairs);
            var render = R1Transcript.Render(res, Opt(sb, true, 1), SyntheticTask);
            Assert.Contains("\"probe_repair_budget\": 1", render, StringComparison.Ordinal);
            Assert.Contains("\"probe_repairs\": 1", render, StringComparison.Ordinal);
            Assert.Contains("\"probe_repairs\":1", R1Transcript.Marker(res), StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    /// <summary>②b 对照：同输入轴关 ⇒ 停在坏产物（rc=8 public_probe_unmet, Calls=2）⇒ 轴有判别力。</summary>
    [Fact]
    public async Task ProbeBudget_Off_Same_Input_Stops_At_Unmet()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller(PlanJson(BadAPy), PlanJson(BadAPy), PlanJson(GoodAPy));
            var res = await R1Pipeline.RunAsync(caller, SyntheticTask, Opt(sb, probe: true, maxProbeRepair: 0),
                CancellationToken.None);

            Assert.Equal(2, caller.Calls);
            Assert.Equal(8, res.Rc);
            Assert.Equal("public_probe_unmet", res.Stage);
            Assert.Equal(1, res.Stats.ExecRepairs);
            Assert.Equal(0, res.ProbeRepairs);
            Assert.Contains("\"correctness_asserted\":0", R1Transcript.Marker(res), StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    /// <summary>③ 负控：产物一次即过 ⇒ 轴不会无端多要调用。</summary>
    [Fact]
    public async Task ProbeBudget_On_Does_Not_Spend_When_Product_Is_Fine()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller(PlanJson(GoodAPy));
            var res = await R1Pipeline.RunAsync(caller, SyntheticTask, Opt(sb, probe: true, maxProbeRepair: 1),
                CancellationToken.None);

            Assert.Equal(0, res.Rc);
            Assert.Equal(1, caller.Calls);
            Assert.Equal(0, res.ProbeRepairs);
            Assert.Equal(0, res.Stats.ExecRepairs);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    /// <summary>④ 判别性负控 + 必要性反证：轴的作用面**只能是探针面**。
    ///   (a) 无探针面 ⇒ 轴 inert（ProbeRepairs=0；坏产物被模型自撰期望放过 ⇒ rc=0, Calls=1）；
    ///   (b) 同产物同轴、只把探针面打开 ⇒ 轴立即生效（Calls=2, ProbeRepairs=1）。</summary>
    [Fact]
    public async Task ProbeBudget_Without_Probe_Is_Inert_And_Probe_Face_Is_Its_Domain()
    {
        var sbA = NewSandbox();
        var sbB = NewSandbox();
        try
        {
            var noProbe = new ScriptedCaller(PlanJson(BadAPy), PlanJson(GoodAPy));
            var resA = await R1Pipeline.RunAsync(noProbe, SyntheticTask, Opt(sbA, probe: false, maxProbeRepair: 1),
                CancellationToken.None);
            Assert.Equal(1, noProbe.Calls);
            Assert.Equal(0, resA.Rc);
            Assert.Equal(0, resA.ProbeRepairs);
            Assert.Null(resA.Probe);

            var withProbe = new ScriptedCaller(PlanJson(BadAPy), PlanJson(GoodAPy));
            var resB = await R1Pipeline.RunAsync(withProbe, SyntheticTask, Opt(sbB, probe: true, maxProbeRepair: 1),
                CancellationToken.None);
            Assert.Equal(2, withProbe.Calls);
            Assert.Equal(0, resB.Rc);
            Assert.Equal(1, resB.ProbeRepairs);
            Assert.Equal(0, resB.Stats.ExecRepairs);
        }
        finally
        {
            Directory.Delete(sbA, true);
            Directory.Delete(sbB, true);
        }
    }

    /// <summary>⑤ 上界：产物始终不合格 ⇒ 调用数有界（1 + 探针预算 + 执行预算），不失控。</summary>
    [Fact]
    public async Task ProbeBudget_Is_Bounded_When_Product_Never_Recovers()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller(PlanJson(BadAPy), PlanJson(BadAPy), PlanJson(BadAPy),
                PlanJson(BadAPy), PlanJson(BadAPy), PlanJson(BadAPy));
            var res = await R1Pipeline.RunAsync(caller, SyntheticTask, Opt(sb, probe: true, maxProbeRepair: 3),
                CancellationToken.None);

            Assert.True(res.Rc != 0, "产物始终不合格 ⇒ 不得报 rc=0");
            Assert.True(caller.Calls <= 1 + 3 + 1, "调用数必须 ≤ 1+探针预算+执行预算, 实测 " + caller.Calls);
            Assert.True(res.ProbeRepairs <= 3);
            Assert.Contains("\"correctness_asserted\":0", R1Transcript.Marker(res), StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }
}
