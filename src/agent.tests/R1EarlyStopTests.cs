using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using agent.contract;
using agent.r1;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// R546 · 早停轴（AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL, 默认 0=关）。
///
/// 轴的定义：产物的**题面公开用例**独立回放已经判定不合格（pfail ≥ 阈值）时，
/// 「再回灌一次真证据、再要一次远端调用」的边际价值被质疑 ⇒ 直接走既有终端分类。
///
/// 钉四件事（成对判据 = 正向 + 负控 + 零回归）：
///   ① 轴关（0）⇒ 同输入同产物仍然回灌修复（Calls=2）且台账**无** early_stop_* 字段（零回归／字段缺席可机检）；
///   ② 轴开且 pfail ≥ 阈值 ⇒ 跳过那次修复调用（Calls=1）、rc/stage 沿用既有分类（rc=8 public_probe_unmet）、
///      台账落 early_stop_pfail/early_stop_skipped ⇒ 省下的正是**那一次**不必要的远端请求；
///   ③ 轴开但 pfail &lt; 阈值 ⇒ 不触发（判别性负控：轴不是「一律不回灌」）；
///   ④ 轴只降调用数，不改任何既有字段的取值语义（rc/stage/correctness_asserted 与轴关同形）。
/// </summary>
public class R1EarlyStopTests
{
    private static string NewSandbox()
    {
        var dir = Path.Combine(Path.GetTempPath(), "r1earlystop-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    private static R1Options Opt(string sandbox, bool probe, int earlyStopPfail, int maxExecRepair = 1) =>
        new(sandbox, 1, 60, null, null, "test", maxExecRepair, probe, earlyStopPfail);

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

    /// <summary>① 轴关 = 旧行为（回灌修复照做、台账无早停字段）。</summary>
    [Fact]
    public async Task EarlyStop_Off_Repairs_As_Before_And_No_Ledger_Field()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller(PlanJson(BadAPy), PlanJson(GoodAPy));
            var res = await R1Pipeline.RunAsync(caller, SyntheticTask, Opt(sb, probe: true, earlyStopPfail: 0),
                CancellationToken.None);

            Assert.Equal(0, res.Rc);
            Assert.Equal("done", res.Stage);
            Assert.Equal(2, caller.Calls);
            Assert.Equal(1, res.Stats.ExecRepairs);
            Assert.Equal(0, res.EarlyStopThreshold);
            Assert.Equal(0, res.EarlyStopSkipped);
            Assert.DoesNotContain("early_stop", R1Transcript.Marker(res), StringComparison.Ordinal);
            Assert.DoesNotContain("early_stop", R1Transcript.Render(res, Opt(sb, true, 0), SyntheticTask),
                StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    /// <summary>② 轴开且 pfail ≥ 阈值 ⇒ 跳过修复调用；rc/stage 沿用既有分类；省下 1 次远端请求。</summary>
    [Fact]
    public async Task EarlyStop_Fires_Skips_The_Repair_Call_And_Keeps_Existing_Classification()
    {
        var sb = NewSandbox();
        try
        {
            // 只备一个回包：若轴没生效 ⇒ 第 2 次调用拿到空包 ⇒ 契约失败(rc=4)，本断言会红。
            var caller = new ScriptedCaller(PlanJson(BadAPy));
            var res = await R1Pipeline.RunAsync(caller, SyntheticTask, Opt(sb, probe: true, earlyStopPfail: 1),
                CancellationToken.None);

            Assert.Equal(1, caller.Calls);
            Assert.Equal(8, res.Rc);
            Assert.Equal("public_probe_unmet", res.Stage);
            Assert.Equal(0, res.Stats.ExecRepairs);
            Assert.Equal(1, res.EarlyStopThreshold);
            Assert.Equal(1, res.EarlyStopSkipped);
            Assert.Equal(1, res.Probe!.Failed);
            Assert.Contains("早停轴开", res.Reason, StringComparison.Ordinal);
            Assert.Contains("R1_EARLY_STOP", res.ReplyText, StringComparison.Ordinal);
            Assert.Contains("\"early_stop_pfail\":1", R1Transcript.Marker(res), StringComparison.Ordinal);
            Assert.Contains("\"early_stop_skipped\":1", R1Transcript.Marker(res), StringComparison.Ordinal);
            // 既有语义不被改动：rc=8 仍然不作正确性证据。
            Assert.Contains("\"correctness_asserted\":0", R1Transcript.Marker(res), StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    /// <summary>③ 判别性负控：轴开但 pfail &lt; 阈值 ⇒ 照旧回灌（轴不是「一律不回灌」）。</summary>
    [Fact]
    public async Task EarlyStop_Below_Threshold_Does_Not_Fire()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller(PlanJson(BadAPy), PlanJson(GoodAPy));
            var res = await R1Pipeline.RunAsync(caller, SyntheticTask, Opt(sb, probe: true, earlyStopPfail: 5),
                CancellationToken.None);

            Assert.Equal(2, caller.Calls);
            Assert.Equal(0, res.Rc);
            Assert.Equal(1, res.Stats.ExecRepairs);
            Assert.Equal(5, res.EarlyStopThreshold);
            Assert.Equal(0, res.EarlyStopSkipped);
            Assert.Contains("\"early_stop_skipped\":0", R1Transcript.Marker(res), StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    /// <summary>④ 无探针 ⇒ 早停无从触发（阈值没有可用信号），行为退回旧路径。</summary>
    [Fact]
    public async Task EarlyStop_Without_Probe_Is_Inert()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller(PlanJson(GoodAPy));
            var res = await R1Pipeline.RunAsync(caller, SyntheticTask, Opt(sb, probe: false, earlyStopPfail: 1),
                CancellationToken.None);

            Assert.Equal(0, res.Rc);
            Assert.Equal(1, caller.Calls);
            Assert.Equal(0, res.EarlyStopSkipped);
            Assert.Null(res.Probe);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }
}
