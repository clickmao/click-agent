using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using agent.contract;
using agent.r1;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// R544 · 产物侧独立自检（题面公开用例机械抽取 + 独立回放 + 管道自产证据回灌）。
///
/// 钉四件事（成对判据：正向 + 负控/零回归）：
///   ① **输入面是真题面**：冻结的 `g1` 题面（sha256 已钉）抽出的用例必须逐条等于题面字面
///      （抽不出/抽错 ⇒ 探针喂的是自己编的输入，等于无权判定）；
///   ② **默认关 = 零行为变化**：同产物同参数，开关关 ⇒ rc/stage/台账字段与旧行为逐位一致；
///   ③ **判别力**：错产物 ⇒ 开关开时判 rc=8 public_probe_unmet（成对报、correctness_asserted=0）；
///      对产物 ⇒ 全过且**不增加调用**（探针不是调用放大器）；
///   ④ **回灌的是管道自产证据**：修复轮 user 轮的 <c>[public_probe]</c> 块带题面期望与实测两侧，
///      且原题面仍在、system 仍逐字节 = pin。
/// </summary>
public class R1PublicProbeTests
{
    private static readonly string RepoRoot = FindRepoRoot();

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
        {
            dir = dir.Parent;
        }
        return dir?.FullName ?? ".";
    }

    private const string G1StatementSha = "516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3";

    private static string G1StatementPath =>
        Path.Combine(RepoRoot, "eval", "rover", "r542", "taskset-r542.json");

    /// <summary>合成题面：与 g1 同形（命令占位符 + 分组标题 + 输入:/期望输出: 块）。</summary>
    private const string SyntheticTask =
        "用 Python 3 实现 `games/` 包, 入口 `python3 -m games <game_id>`（`<game_id>` 取 a）。\n\n"
        + "### 游戏 `a`\n输入:\n7\n期望输出:\n14\n\n请把完整程序放在一个 ```python 围栏代码块内。\n";

    private sealed class ScriptedCaller : agent.ILLMCaller
    {
        private readonly Queue<string> _replies;
        public int Calls;
        public string LastSystemPrompt = string.Empty;
        public string LastUserMessage = string.Empty;

        public ScriptedCaller(params string[] replies) => _replies = new Queue<string>(replies);

        public Task<agent.LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
        {
            Calls++;
            LastSystemPrompt = prompt.SystemPrompt;
            LastUserMessage = prompt.UserMessage;
            var content = _replies.Count > 0 ? _replies.Dequeue() : string.Empty;
            return Task.FromResult(new agent.LLMResponse
            {
                Content = content, Success = true,
                PromptTokens = 1000, CompletionTokens = 200,
                CacheHitTokens = 900, CacheMissTokens = 100,
            });
        }
    }

    private static string NewSandbox()
    {
        var dir = Path.Combine(Path.GetTempPath(), "r1probe-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    private static R1Options Opt(string sandbox, bool probe, int maxExecRepair = 0) =>
        new(sandbox, 1, 60, null, null, "test", maxExecRepair, probe);

    private static string Esc(string s) =>
        s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n");

    private static string Step(string id, string path, string content) =>
        "{\"id\":\"" + id + "\",\"tool\":\"write_file\",\"args\":{\"path\":\"" + Esc(path) + "\",\"content\":\""
        + Esc(content) + "\"},\"depends_on\":[]}";

    private const string MainPy =
        "import sys\nfrom games import a\nsys.stdout.write({\"a\": a}[sys.argv[1]].solve(sys.stdin.read()))\n";

    /// <summary>计划 = 写 games/ 包; <paramref name="aPy"/> 决定产物对错（判别力靠它翻转）。</summary>
    private static string PlanJson(string aPy) =>
        "{\"schema_version\":\"r1.0\",\"intent\":\"code_task\",\"confidence\":0.9,\"entities\":[],\"constraints\":[],"
        + "\"missing_slots\":[],\"ambiguities\":[],\"done_when\":[],\"refusal\":null,\"plan\":["
        + Step("s1", "games/__init__.py", "")
        + "," + Step("s2", "games/__main__.py", MainPy)
        + "," + Step("s3", "games/a.py", aPy)
        + "]}";

    private const string GoodAPy = "def solve(text):\n    return str(int(text.split()[0]) * 2)\n";
    private const string BadAPy = "def solve(text):\n    return str(int(text.split()[0]) * 3)\n";

    // ---------- ① 输入面 ----------

    [Fact]
    public void Extractor_Rejects_Statement_Without_Placeholder()
    {
        Assert.False(PublicExampleExtractor.TryExtract("### 游戏 `a`\n输入:\n1\n期望输出:\n2\n",
            out _, out var reason));
        Assert.Equal("no_command_placeholder", reason);
    }

    [Fact]
    public void Extractor_Rejects_Statement_Without_Example_Blocks()
    {
        Assert.False(PublicExampleExtractor.TryExtract("入口 `python3 -m games <game_id>`（`<game_id>` 取 a）。\n",
            out _, out var reason));
        Assert.Equal("no_example_blocks", reason);
    }

    [Fact]
    public void Extractor_Reads_Synthetic_Statement_Verbatim()
    {
        Assert.True(PublicExampleExtractor.TryExtract(SyntheticTask, out var set, out var reason));
        Assert.Equal("ok", reason);
        Assert.Equal("python3 -m games ", set.CommandPrefix);
        Assert.Single(set.Examples);
        Assert.Equal("a", set.Examples[0].GameId);
        Assert.Equal("7", set.Examples[0].Input);
        Assert.Equal("14", set.Examples[0].Expected);
    }

    /// <summary>真题面锚：冻结的 `g1` 声明 sha 必须自洽，且抽出的 8 条公开用例逐条等于题面字面。</summary>
    [Fact]
    public void Extractor_Reads_Frozen_G1_Statement()
    {
        Assert.True(File.Exists(G1StatementPath), "缺冻结题集: " + G1StatementPath);
        using var doc = JsonDocument.Parse(File.ReadAllText(G1StatementPath));
        var task = doc.RootElement.GetProperty("tasks")[0];
        var prompt = task.GetProperty("prompt").GetString()!;
        Assert.Equal(G1StatementSha, task.GetProperty("prompt_sha256").GetString());
        Assert.Equal(G1StatementSha, R1Hash.OfText(prompt));

        Assert.True(PublicExampleExtractor.TryExtract(prompt, out var set, out _));
        Assert.Equal("python3 -m games ", set.CommandPrefix);
        Assert.Equal(8, set.Examples.Count);                       // 4 分组 x 2 例（题面 meta.public=8）

        var byGroup = new Dictionary<string, List<PublicExample>>();
        foreach (var e in set.Examples)
        {
            if (!byGroup.TryGetValue(e.GameId, out var list))
            {
                list = new List<PublicExample>();
                byGroup[e.GameId] = list;
            }
            list.Add(e);
        }
        Assert.Equal(new[] { "life", "sub", "nim", "wythoff" }, new List<string>(byGroup.Keys));

        // 逐条字面锚（题面里逐字写着这些行；抽错 ⇒ 探针喂的就不是题面契约）
        var wythoff = byGroup["wythoff"];
        Assert.Equal("21 25", wythoff[0].Input);
        Assert.Equal("WIN 15 15", wythoff[0].Expected);
        Assert.Equal("10 9", wythoff[1].Input);
        Assert.Equal("WIN 0 3", wythoff[1].Expected);

        Assert.Equal("31 3\n1 6 10", byGroup["sub"][0].Input);
        Assert.Equal("WIN 6", byGroup["sub"][0].Expected);
        Assert.Equal("3\n5 9 4", byGroup["nim"][0].Input);
        Assert.Equal("WIN 2 8", byGroup["nim"][0].Expected);

        var life = byGroup["life"][0];
        Assert.StartsWith("11 5 4\n#....", life.Input, StringComparison.Ordinal);
        Assert.Equal(11, life.Expected.Split('\n').Length);         // 11 行网格, 且未被指示行污染
        Assert.Contains(".###.", life.Expected, StringComparison.Ordinal);
        Assert.DoesNotContain("请把", life.Expected, StringComparison.Ordinal);
    }

    // ---------- ③ 判别力（探针自身） ----------

    [Fact]
    public async Task Probe_Flags_Wrong_Artifact_And_Passes_Correct_One()
    {
        var sb = NewSandbox();
        var other = NewSandbox();
        try
        {
            WritePackage(sb, GoodAPy);
            WritePackage(other, BadAPy);
            Assert.True(PublicExampleExtractor.TryExtract(SyntheticTask, out var set, out _));

            var ok = await PublicExampleProbe.RunAsync(set, sb, 30, CancellationToken.None);
            Assert.True(ok.Ran);
            Assert.Equal(1, ok.Total);
            Assert.Equal(0, ok.Failed);
            Assert.Equal("public_examples_pass", ok.Reason);

            var bad = await PublicExampleProbe.RunAsync(set, other, 30, CancellationToken.None);
            Assert.True(bad.Ran);
            Assert.Equal(1, bad.Failed);
            Assert.Contains("期望=`14`", bad.Failures[0], StringComparison.Ordinal);
            Assert.Contains("实测 rc=0 stdout=`21`", bad.Failures[0], StringComparison.Ordinal);

            // 负控: 沙箱不存在 ⇒ 显式弃权(不冒充通过)
            var gone = await PublicExampleProbe.RunAsync(set, Path.Combine(sb, "nope"), 30, CancellationToken.None);
            Assert.False(gone.Ran);
            Assert.Equal("sandbox_missing", gone.Reason);
        }
        finally
        {
            Directory.Delete(sb, true);
            Directory.Delete(other, true);
        }
    }

    private static void WritePackage(string root, string aPy)
    {
        Directory.CreateDirectory(Path.Combine(root, "games"));
        File.WriteAllText(Path.Combine(root, "games", "__init__.py"), string.Empty);
        File.WriteAllText(Path.Combine(root, "games", "__main__.py"), MainPy);
        File.WriteAllText(Path.Combine(root, "games", "a.py"), aPy);
    }

    // ---------- ② 默认关 = 零行为变化（成对） ----------

    [Fact]
    public async Task Probe_Off_Is_Byte_For_Byte_Old_Behavior_On_Same_Artifact()
    {
        var offSb = NewSandbox();
        var onSb = NewSandbox();
        try
        {
            var offCaller = new ScriptedCaller(PlanJson(BadAPy));
            var off = await R1Pipeline.RunAsync(offCaller, SyntheticTask, Opt(offSb, probe: false), CancellationToken.None);
            Assert.Equal(0, off.Rc);
            Assert.Equal("done", off.Stage);
            Assert.Equal(1, offCaller.Calls);
            Assert.Null(off.Probe);
            Assert.DoesNotContain("public_probe", R1Transcript.Marker(off), StringComparison.Ordinal);

            var onCaller = new ScriptedCaller(PlanJson(BadAPy), PlanJson(BadAPy));
            var on = await R1Pipeline.RunAsync(onCaller, SyntheticTask, Opt(onSb, probe: true), CancellationToken.None);
            Assert.Equal(8, on.Rc);
            Assert.Equal("public_probe_unmet", on.Stage);
        }
        finally
        {
            Directory.Delete(offSb, true);
            Directory.Delete(onSb, true);
        }
    }

    // ---------- ④ 回灌 + 恢复 / 不增加调用 ----------

    [Fact]
    public async Task Probe_Repair_Round_Reinjects_Pipeline_Evidence_Then_Recovers()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller(PlanJson(BadAPy), PlanJson(GoodAPy));
            var res = await R1Pipeline.RunAsync(caller, SyntheticTask, Opt(sb, probe: true, maxExecRepair: 1),
                CancellationToken.None);

            Assert.Equal(0, res.Rc);
            Assert.Equal("done", res.Stage);
            Assert.Equal(2, caller.Calls);
            Assert.Equal(1, res.Stats.ExecRepairs);
            Assert.NotNull(res.Probe);
            Assert.Equal(0, res.Probe!.Failed);
            Assert.Contains("\"public_probe_failed\":0", R1Transcript.Marker(res), StringComparison.Ordinal);

            // 回灌 = 管道自产证据（期望/实测两侧 + 题面原样 + 前缀不动 + 标记）
            Assert.Contains("[public_probe]", caller.LastUserMessage, StringComparison.Ordinal);
            Assert.Contains("期望=`14`", caller.LastUserMessage, StringComparison.Ordinal);
            Assert.Contains("实测 rc=0 stdout=`21`", caller.LastUserMessage, StringComparison.Ordinal);
            Assert.Contains("非你的自述", caller.LastUserMessage, StringComparison.Ordinal);
            Assert.Contains("用 Python 3 实现", caller.LastUserMessage, StringComparison.Ordinal);
            Assert.Equal(StructuredPrompt.Prefix, caller.LastSystemPrompt);
            Assert.Contains("R1_PUBLIC_PROBE", res.ReplyText, StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    [Fact]
    public async Task Probe_On_Correct_Artifact_Adds_No_Call_And_Says_Why()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller(PlanJson(GoodAPy));
            var res = await R1Pipeline.RunAsync(caller, SyntheticTask, Opt(sb, probe: true), CancellationToken.None);

            Assert.Equal(0, res.Rc);
            Assert.Equal(1, caller.Calls);
            Assert.Equal(0, res.Stats.ExecRepairs);
            Assert.NotNull(res.Probe);
            Assert.Equal(1, res.Probe!.Total);
            Assert.Equal(0, res.Probe.Failed);
            Assert.Contains("题面公开用例回放 1/1 过", res.Reason, StringComparison.Ordinal);
            Assert.Contains("\"public_probe_failed\":0", R1Transcript.Marker(res), StringComparison.Ordinal);
            Assert.Contains("\"correctness_asserted\":1", R1Transcript.Marker(res), StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    /// <summary>探针在「抽不出用例」的题面上必须完全退场（零行为变化），即便开关打开。</summary>
    [Fact]
    public async Task Probe_Stays_Out_When_Statement_Has_No_Examples()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller(PlanJson(BadAPy));
            var res = await R1Pipeline.RunAsync(caller, "写个游戏包\n", Opt(sb, probe: true), CancellationToken.None);
            Assert.Equal(0, res.Rc);
            Assert.Equal(1, caller.Calls);
            Assert.Null(res.Probe);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }
}
