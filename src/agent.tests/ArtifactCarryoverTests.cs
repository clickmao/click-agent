using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.r1;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// R600 · 修复环「带现状」（AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER，默认 **开**）。
///
/// 定因：R585–R599 失败例次 100% 集中 wythoff 族（主桶=冷集构造层）；R600 实测失败臂产物在**题面公开
/// 用例**上即失败，而管道已机械回放该用例、已花掉一次回灌修复，仍以同错类交付 ⇒ 病灶 = 管道无状态
/// （模型只产契约），修复轮不带模型上次写下的产物 ⇒ 盲修。
///
/// 钉六件事（正控 + 判别性负控 + 零回归 + 预算 + 边界）：
///   ① 正控：轴开 ⇒ 修复轮 user 轮含盘上产物原文 + `R1_ARTIFACT_CARRYOVER` 打点；首轮（非修复轮）**不含**；
///   ② 零回归：同场景轴关 ⇒ 修复轮 user 轮**不含** `[artifact]`、无打点，且轴开的消息 = 轴关消息 + 追加块
///      （逐位前缀关系 ⇒ 只增不改，调用数同为 2 ⇒ 同预算）；
///   ③ 现状性：盘上原文（含 sha12/字节数）随附，同一 path 多次写盘取**最后一次**；
///   ④ 预算：单文件超限 ⇒ 按字节截断 + 显式标记；总量超限 ⇒ 尾注列出「未随附」；
///   ⑤ 边界（负控有牙）：越界路径 / 盘上缺失 ⇒ 只列名不随附；生成物目录（`__pycache__`）**静默跳过**（不入任何列表）；
///      二进制（含 NUL）⇒ 只报大小不搬内容；
///   ⑥ 轴解析：缺省 = 开；`0`/`off`/`false` ⇒ 关（关态即旧行为）。
/// </summary>
public class ArtifactCarryoverTests
{
    private static string NewSandbox()
    {
        var dir = Path.Combine(Path.GetTempPath(), "r600carry-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    private static StepOutcome Wrote(string id, string path) =>
        StepOutcome.Write(id, path, "0de0de0de0de0de0", 1);

    private static string Joined(IReadOnlyList<string> lines) => string.Join("\n", lines);

    private static void Put(string sandbox, string rel, string content)
    {
        var full = Path.Combine(sandbox, rel);
        Directory.CreateDirectory(Path.GetDirectoryName(full)!);
        File.WriteAllBytes(full, new UTF8Encoding(false).GetBytes(content));
    }

    private static void PutBytes(string sandbox, string rel, byte[] bytes)
    {
        var full = Path.Combine(sandbox, rel);
        Directory.CreateDirectory(Path.GetDirectoryName(full)!);
        File.WriteAllBytes(full, bytes);
    }

    /// <summary>① + ③ 正控：随附盘上原文（sha12/字节数）、首轮不含、同 path 取最后一次写。</summary>
    [Fact]
    public void Render_Carries_OnDisk_Bytes_With_Sha_And_Takes_Last_Write()
    {
        var sb = NewSandbox();
        try
        {
            Put(sb, "games/a.py", "def solve(text):\n    return 'OLD'\n");
            Put(sb, "games/__main__.py", "import sys\nprint('entry')\n");
            var lines = ArtifactCarryover.Render(sb, new[]
            {
                Wrote("s0", "games/a.py"),
                Wrote("s1", "games/__main__.py"),
                Wrote("s2", "games/a.py"),
            });
            var all = Joined(lines);

            Assert.NotEmpty(lines);
            Assert.Contains("[artifact]", lines[0], StringComparison.Ordinal);
            Assert.Contains("--- games/a.py (", all, StringComparison.Ordinal);
            Assert.Contains("--- end games/a.py ---", all, StringComparison.Ordinal);
            Assert.Contains("def solve(text):", all, StringComparison.Ordinal);
            Assert.Contains(R1Hash.OfText("def solve(text):\n    return 'OLD'\n").Substring(0, 12), all, StringComparison.Ordinal);
            // 同一 path 只随附一次（最后一次写），且按**最后一次写盘序**（__main__.py 的最后写在 a.py 之前）
            Assert.Equal(1, Count(all, "--- games/a.py ("));
            Assert.True(all.IndexOf("--- games/__main__.py (", StringComparison.Ordinal)
                < all.IndexOf("--- games/a.py (", StringComparison.Ordinal));
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    /// <summary>④ 预算：单文件截断留标记；总量超限列「未随附」。</summary>
    [Fact]
    public void Render_Truncates_PerFile_And_Lists_Over_Budget()
    {
        var sb = NewSandbox();
        try
        {
            Put(sb, "big.py", new string('x', 5000));
            Put(sb, "second.py", "print('second')\n");

            var perFile = ArtifactCarryover.Render(sb, new[] { Wrote("s1", "big.py") }, 64, 16384);
            Assert.Contains("截断", Joined(perFile), StringComparison.Ordinal);
            Assert.Contains("5000", Joined(perFile), StringComparison.Ordinal);
            Assert.Contains("64", Joined(perFile), StringComparison.Ordinal);

            // 总量超限：超预算者列名不搬内容、后续小文件仍随附（贪心覆盖，不整批放弃）
            var tight = ArtifactCarryover.Render(sb, new[] { Wrote("s1", "big.py"), Wrote("s2", "second.py") }, 2048, 2048);
            var tightAll = Joined(tight);
            Assert.Contains("未随附", tightAll, StringComparison.Ordinal);
            Assert.Contains("big.py", tightAll, StringComparison.Ordinal);
            Assert.Contains("预算用尽", tightAll, StringComparison.Ordinal);
            Assert.Contains("print('second')", tightAll, StringComparison.Ordinal);

            // 小预算：首个文件装得下、第二个装不下 ⇒ 只列名不搬内容（预算不吃超）
            Put(sb, "f1.py", new string('a', 1200));
            Put(sb, "f2.py", "SECONDONLY\n");
            var small = ArtifactCarryover.Render(sb, new[] { Wrote("s1", "f1.py"), Wrote("s2", "f2.py") }, 4096, 1300);
            Assert.Contains("--- f1.py (", Joined(small), StringComparison.Ordinal);
            Assert.Contains("未随附", Joined(small), StringComparison.Ordinal);
            Assert.Contains("预算用尽", Joined(small), StringComparison.Ordinal);
            Assert.Contains("f2.py", Joined(small), StringComparison.Ordinal);
            Assert.DoesNotContain("SECONDONLY", Joined(small), StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    /// <summary>⑤ 边界负控：越界/缺失/生成物/二进制四类都不得被当作原文搬进来。</summary>
    [Fact]
    public void Render_Never_Carries_Escaping_Missing_Generated_Or_Binary()
    {
        var sb = NewSandbox();
        try
        {
            Put(sb, "ok.py", "print(1)\n");
            PutBytes(sb, "bin.pyc", new byte[] { 0x61, 0x00, 0x62, 0x63 });
            var outside = Path.Combine(Path.GetDirectoryName(sb)!, "r600-outside.txt");
            File.WriteAllText(outside, "SECRET-OUTSIDE");

            var lines = ArtifactCarryover.Render(sb, new[]
            {
                Wrote("s1", "../r600-outside.txt"),
                Wrote("s2", "missing.py"),
                Wrote("s3", "__pycache__/ok.cpython-311.pyc"),
                Wrote("s4", "bin.pyc"),
                Wrote("s5", "ok.py"),
            });
            var all = Joined(lines);

            Assert.DoesNotContain("SECRET-OUTSIDE", all, StringComparison.Ordinal);
            Assert.Contains("越界", all, StringComparison.Ordinal);
            Assert.Contains("盘上不存在", all, StringComparison.Ordinal);
            Assert.DoesNotContain("__pycache__", all, StringComparison.Ordinal);
            Assert.Contains("含 NUL", all, StringComparison.Ordinal);
            Assert.Contains("print(1)", all, StringComparison.Ordinal);
            File.Delete(outside);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    /// <summary>空输入 ⇒ 空列表（契约/闸拒答等无写盘路径不产生尾巴）。</summary>
    [Fact]
    public void Render_NoWriteSteps_IsEmpty()
    {
        var sb = NewSandbox();
        try
        {
            Assert.Empty(ArtifactCarryover.Render(sb, Array.Empty<StepOutcome>()));
            Assert.Empty(ArtifactCarryover.Render(sb, new[] { StepOutcome.Run("s1", 0, "x", "", 3) }));
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    /// <summary>⑥ 轴解析：缺省开；0/off/false 关。</summary>
    [Fact]
    public void Options_Axis_Defaults_On_And_Parses_Off()
    {
        var sb = NewSandbox();
        var prev = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER");
        try
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER", null);
            Assert.True(R1Options.FromEnvironment(sb).ArtifactCarryoverEnabled);

            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER", "0");
            Assert.False(R1Options.FromEnvironment(sb).ArtifactCarryoverEnabled);

            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER", "off");
            Assert.False(R1Options.FromEnvironment(sb).ArtifactCarryoverEnabled);

            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER", "1");
            Assert.True(R1Options.FromEnvironment(sb).ArtifactCarryoverEnabled);
        }
        finally
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER", prev);
            Directory.Delete(sb, true);
        }
    }

    // ---------- 管道级：正控 + 零回归（同一场景两档对照） ----------

    private sealed class ScriptedCaller : agent.ILLMCaller
    {
        private readonly Queue<string> _replies;
        public readonly List<Prompt> Seen = new List<Prompt>();

        public ScriptedCaller(params string[] replies) => _replies = new Queue<string>(replies);

        public Task<agent.LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
        {
            Seen.Add(prompt);
            var content = _replies.Count > 0 ? _replies.Dequeue() : string.Empty;
            return Task.FromResult(new agent.LLMResponse
            {
                Content = content,
                Success = true,
                PromptTokens = 1000,
                CompletionTokens = 200,
                CacheHitTokens = 900,
                CacheMissTokens = 100,
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

    private static R1Options Opt(string sandbox, bool carryover) =>
        new(sandbox, 1, 60, null, null, "test", 1, true, 0, 0, carryover);

    /// <summary>①② 正控 + 零回归：同场景两档 ⇒ 轴开 = 轴关 + 追加块（逐位前缀），调用数同为 2（同预算）。</summary>
    [Fact]
    public async Task RepairPrompt_Carries_Artifacts_When_On_And_Is_Untouched_When_Off()
    {
        var sbOff = NewSandbox();
        var sbOn = NewSandbox();
        try
        {
            var offCaller = new ScriptedCaller(PlanJson(BadAPy), PlanJson(GoodAPy));
            var off = await R1Pipeline.RunAsync(offCaller, SyntheticTask, Opt(sbOff, carryover: false), CancellationToken.None);

            var onCaller = new ScriptedCaller(PlanJson(BadAPy), PlanJson(GoodAPy));
            var on = await R1Pipeline.RunAsync(onCaller, SyntheticTask, Opt(sbOn, carryover: true), CancellationToken.None);

            // 两侧都修到 done（场景同解）⇒ 差异只在「修复轮看到了什么」
            Assert.Equal(0, off.Rc);
            Assert.Equal(0, on.Rc);
            Assert.Equal(2, offCaller.Seen.Count);
            Assert.Equal(2, onCaller.Seen.Count);

            var offMsg = offCaller.Seen[1].UserMessage;
            var onMsg = onCaller.Seen[1].UserMessage;

            // ② 零回归：轴关 ⇒ 修复轮无产物块、无打点
            Assert.DoesNotContain("[artifact]", offMsg, StringComparison.Ordinal);
            Assert.Equal(0, off.ArtifactCarryoverRounds);
            Assert.DoesNotContain("artifact_carryover", R1Transcript.Marker(off), StringComparison.Ordinal);

            // ① 正控：轴开 ⇒ 修复轮带盘上原文 + 打点；且只在该修复块**内**追加（去掉闭合标记后轴开 = 轴关 + 追加块）
            const string Close = "</repair>";
            Assert.EndsWith(Close, offMsg, StringComparison.Ordinal);
            var inner = offMsg.Substring(0, offMsg.Length - Close.Length);
            var diff = FirstDiff(inner, onMsg);
            if (diff != inner.Length)
            {
                var from = Math.Max(0, diff - 40);
                Assert.Fail("修复轮消息在位置 " + diff + " 处不同: off=`"
                    + Slice(inner, from, 90) + "` on=`" + Slice(onMsg, from, 90) + "`");
            }
            var tail = onMsg.Substring(inner.Length);
            Assert.Contains("[artifact]", tail, StringComparison.Ordinal);
            Assert.Contains("--- games/a.py (", tail, StringComparison.Ordinal);
            Assert.Contains("return str(int(text.split()[0]) * 3)", tail, StringComparison.Ordinal);
            Assert.EndsWith(Close, onMsg, StringComparison.Ordinal);
            Assert.Equal(1, on.ArtifactCarryoverRounds);
            Assert.True(on.ArtifactCarryoverChars > 0);
            Assert.Contains("\"artifact_carryover_rounds\":1", R1Transcript.Marker(on), StringComparison.Ordinal);
            Assert.Contains("\"artifact_carryover_enabled\": 1", R1Transcript.Render(on, Opt(sbOn, true), SyntheticTask), StringComparison.Ordinal);

            // ③ 判别性负控：首轮（非修复轮）两档都不含产物块
            Assert.DoesNotContain("[artifact]", offCaller.Seen[0].UserMessage, StringComparison.Ordinal);
            Assert.DoesNotContain("[artifact]", onCaller.Seen[0].UserMessage, StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sbOff, true);
            Directory.Delete(sbOn, true);
        }
    }

    /// <summary>④ 反例（有牙）：一次即过 ⇒ 不产生随附（机制不得无差别触发）。</summary>
    [Fact]
    public async Task RepairPrompt_Not_Carried_When_No_Repair_Happens()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller(PlanJson(GoodAPy));
            var res = await R1Pipeline.RunAsync(caller, SyntheticTask, Opt(sb, carryover: true), CancellationToken.None);

            Assert.Equal(0, res.Rc);
            Assert.Single(caller.Seen);
            Assert.DoesNotContain("[artifact]", caller.Seen[0].UserMessage, StringComparison.Ordinal);
            Assert.Equal(0, res.ArtifactCarryoverRounds);
            Assert.DoesNotContain("artifact_carryover_rounds", R1Transcript.Marker(res), StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    private static int FirstDiff(string a, string b)
    {
        var n = Math.Min(a.Length, b.Length);
        for (var i = 0; i < n; i++)
        {
            if (a[i] != b[i])
            {
                return i;
            }
        }
        return n;
    }

    private static string Slice(string s, int from, int len)
    {
        if (from >= s.Length)
        {
            return "(尾)";
        }
        var take = Math.Min(len, s.Length - from);
        return s.Substring(from, take).Replace("\n", "\\n");
    }

    private static int Count(string haystack, string needle)
    {
        var n = 0;
        var i = haystack.IndexOf(needle, StringComparison.Ordinal);
        while (i >= 0)
        {
            n++;
            i = haystack.IndexOf(needle, i + needle.Length, StringComparison.Ordinal);
        }
        return n;
    }
}
