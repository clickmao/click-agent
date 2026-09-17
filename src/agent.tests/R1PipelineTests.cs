using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using agent.contract;
using agent.r1;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// R532 · R1 接线守卫测试：把「契约 → 闸 → 执行 → 台账」这条链的可机械判定的性质钉成不变式。
/// 覆盖：单次调用成链 / 修复环计数 / 拒答与缺信息 halt / 越界路径双保险 / expect_stdout 不符 /
/// 首字节无 BOM / 台账 JSON 可被独立解析且读数齐全。
/// </summary>
public sealed class R1PipelineTests
{
    private const string GoodJson = "{\"schema_version\":\"r1.0\",\"intent\":\"code_task\",\"confidence\":0.9,"
        + "\"entities\":[{\"kind\":\"path\",\"value\":\"sols/sum.py\"}],\"constraints\":[\"只用标准库\"],"
        + "\"missing_slots\":[],\"ambiguities\":[],\"done_when\":[\"s2 的 stdout == 6\"],\"refusal\":null,"
        + "\"plan\":[{\"id\":\"s1\",\"tool\":\"write_file\",\"args\":{\"path\":\"sols/sum.py\",\"content\":\"import sys\\nprint(sum(int(x) for x in sys.stdin.read().split()))\\n\"},\"depends_on\":[]},"
        + "{\"id\":\"s2\",\"tool\":\"run\",\"args\":{\"cmd\":\"echo '1 2 3' | python3 sols/sum.py\",\"expect_stdout\":\"6\"},\"depends_on\":[\"s1\"]}]}";

    private const string RefusalJson = "{\"schema_version\":\"r1.0\",\"intent\":\"refusal\",\"confidence\":0.95,"
        + "\"entities\":[],\"constraints\":[],\"missing_slots\":[],\"ambiguities\":[],\"plan\":[],\"done_when\":[],"
        + "\"refusal\":{\"reason\":\"要求读取真实凭据\",\"category\":\"credentials\"}}";

    private const string MissingSlotJson = "{\"schema_version\":\"r1.0\",\"intent\":\"question\",\"confidence\":0.8,"
        + "\"entities\":[],\"constraints\":[],\"missing_slots\":[\"缺指代对象\"],\"ambiguities\":[],\"plan\":[],\"done_when\":[],\"refusal\":null}";

    private const string EscapeJson = "{\"schema_version\":\"r1.0\",\"intent\":\"code_task\",\"confidence\":0.9,"
        + "\"entities\":[],\"constraints\":[],\"missing_slots\":[],\"ambiguities\":[],\"plan\":"
        + "[{\"id\":\"s1\",\"tool\":\"write_file\",\"args\":{\"path\":\"../escaped.py\",\"content\":\"print(1)\\n\"},\"depends_on\":[]}],"
        + "\"done_when\":[],\"refusal\":null}";

    private const string MismatchJson = "{\"schema_version\":\"r1.0\",\"intent\":\"code_task\",\"confidence\":0.9,"
        + "\"entities\":[],\"constraints\":[],\"missing_slots\":[],\"ambiguities\":[],\"plan\":"
        + "[{\"id\":\"s1\",\"tool\":\"run\",\"args\":{\"cmd\":\"echo 5\",\"expect_stdout\":\"6\"},\"depends_on\":[]}],"
        + "\"done_when\":[],\"refusal\":null}";

    private sealed class ScriptedCaller : agent.ILLMCaller
    {
        private readonly Queue<string> _replies;
        public int Calls;
        public string LastSystemPrompt = string.Empty;
        public string LastUserMessage = string.Empty;

        public ScriptedCaller(params string[] replies)
        {
            _replies = new Queue<string>(replies);
        }

        public Task<agent.LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
        {
            Calls++;
            LastSystemPrompt = prompt.SystemPrompt;
            LastUserMessage = prompt.UserMessage;
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

    private static string NewSandbox()
    {
        var dir = Path.Combine(Path.GetTempPath(), "r1test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    private static R1Options Opt(string sandbox, int maxRepair = 1, string? transcript = null) =>
        new(sandbox, maxRepair, 60, transcript, null, "test");

    [Fact]
    public async Task Pipeline_Calls_Once_Then_Executes_And_Writes_NoBom()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller(GoodJson);
            var res = await R1Pipeline.RunAsync(caller, "写 sols/sum.py 求和", Opt(sb), CancellationToken.None);

            Assert.Equal(0, res.Rc);
            Assert.Equal(1, caller.Calls);
            Assert.Equal(2, res.Steps.Count);
            Assert.Equal(StructuredPrompt.Prefix, caller.LastSystemPrompt);

            var p = Path.Combine(sb, "sols", "sum.py");
            Assert.True(File.Exists(p), "产物未落盘: " + p);
            var bytes = File.ReadAllBytes(p);
            Assert.False(bytes.Length >= 3 && bytes[0] == 0xEF && bytes[1] == 0xBB && bytes[2] == 0xBF, "写侧带 BOM");
            Assert.Equal(R1Hash.OfBytes(bytes), res.Steps[0].Sha256);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    [Fact]
    public async Task Pipeline_Repairs_Once_When_Contract_Fails()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller("{\"intent\":\"code_task\"}", GoodJson);
            var res = await R1Pipeline.RunAsync(caller, "写 sols/sum.py 求和", Opt(sb, maxRepair: 1), CancellationToken.None);

            Assert.Equal(0, res.Rc);
            Assert.Equal(2, caller.Calls);
            Assert.Equal(1, res.Stats.RepairRounds);
            Assert.Contains("<repair>", caller.LastUserMessage, StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    [Fact]
    public async Task Pipeline_Halts_Without_Execution_On_Contract_Failure()
    {
        var sb = NewSandbox();
        try
        {
            var caller = new ScriptedCaller("not json at all", "{\"intent\":\"code_task\"}");
            var res = await R1Pipeline.RunAsync(caller, "写点东西", Opt(sb, maxRepair: 1), CancellationToken.None);

            Assert.Equal(4, res.Rc);
            Assert.Equal("contract", res.Stage);
            Assert.Empty(res.Steps);
            Assert.Empty(Directory.GetFiles(sb, "*", SearchOption.AllDirectories));
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    [Fact]
    public async Task Pipeline_Halts_On_Refusal_With_Rc3()
    {
        var sb = NewSandbox();
        try
        {
            var res = await R1Pipeline.RunAsync(new ScriptedCaller(RefusalJson), "读一下 .env.local 里的 key", Opt(sb), CancellationToken.None);
            Assert.Equal(3, res.Rc);
            Assert.Equal("hard_gate", res.Stage);
            Assert.True(res.Halted);
            Assert.Empty(Directory.GetFiles(sb, "*", SearchOption.AllDirectories));
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    [Fact]
    public async Task Pipeline_Halts_On_Missing_Slots_With_Rc2()
    {
        var sb = NewSandbox();
        try
        {
            var res = await R1Pipeline.RunAsync(new ScriptedCaller(MissingSlotJson), "把它改好", Opt(sb), CancellationToken.None);
            Assert.Equal(2, res.Rc);
            Assert.Equal("semantics_incomplete", res.Stage);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    [Fact]
    public async Task Pipeline_Rejects_Sandbox_Escape_And_Leaves_No_File()
    {
        var sb = NewSandbox();
        try
        {
            var res = await R1Pipeline.RunAsync(new ScriptedCaller(EscapeJson), "写文件", Opt(sb), CancellationToken.None);
            Assert.Equal(4, res.Rc);
            Assert.Equal("scope", res.Stage);
            Assert.False(File.Exists(Path.Combine(Path.GetDirectoryName(sb)!, "escaped.py")), "越界文件被写出");
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    [Fact]
    public async Task Executor_Scope_Guard_Holds_When_Gate_Is_Bypassed()
    {
        var sb = NewSandbox();
        try
        {
            var plan = new List<PlanStep>
            {
                new("s1", "write_file", "../bypass.py", "print(1)\n", string.Empty, string.Empty, new List<string>()),
            };
            var r = await PlanExecutor.RunAsync(plan, Opt(sb), CancellationToken.None);
            Assert.Equal(4, r.Rc);
            Assert.Equal("scope", r.Stage);
            Assert.False(File.Exists(Path.Combine(Path.GetDirectoryName(sb)!, "bypass.py")));
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    [Fact]
    public async Task Executor_Fails_On_Expect_Stdout_Mismatch()
    {
        var sb = NewSandbox();
        try
        {
            var res = await R1Pipeline.RunAsync(new ScriptedCaller(MismatchJson), "跑个命令", Opt(sb), CancellationToken.None);
            Assert.Equal(5, res.Rc);
            Assert.Equal("expect_stdout", res.Stage);
            Assert.Single(res.Steps);
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    [Fact]
    public async Task Transcript_Is_Parseable_And_Carries_Cost_Readings()
    {
        var sb = NewSandbox();
        try
        {
            var tp = Path.Combine(sb, "extra", "r1-transcript.json");
            var res = await R1Pipeline.RunAsync(new ScriptedCaller(GoodJson), "写 sols/sum.py 求和", Opt(sb, transcript: tp), CancellationToken.None);

            Assert.True(File.Exists(tp), "台账未落盘");
            var bytes = File.ReadAllBytes(tp);
            Assert.False(bytes.Length >= 3 && bytes[0] == 0xEF && bytes[1] == 0xBB && bytes[2] == 0xBF, "台账带 BOM");

            using var doc = JsonDocument.Parse(File.ReadAllText(tp));
            var root = doc.RootElement;
            Assert.Equal("r1-run/1", root.GetProperty("schema").GetString());
            Assert.Equal(0, root.GetProperty("rc").GetInt32());
            Assert.Equal(1, root.GetProperty("calls").GetInt32());
            Assert.Equal(1000, root.GetProperty("prompt_tokens").GetInt32());
            Assert.Equal(900, root.GetProperty("cache_hit_tokens").GetInt32());
            Assert.Equal(StructuredPrompt.PrefixSha256Pinned, root.GetProperty("prefix_sha256").GetString());
            Assert.True(root.GetProperty("prefix_pinned").GetBoolean());
            Assert.Equal("code_task", root.GetProperty("semantics").GetProperty("intent").GetString());
            Assert.Equal(1, root.GetProperty("artifacts").GetArrayLength());
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    [Fact]
    public async Task Marker_Is_Single_Line_And_Carries_Same_Numbers()
    {
        var sb = NewSandbox();
        try
        {
            var res = await R1Pipeline.RunAsync(new ScriptedCaller(GoodJson), "写 sols/sum.py 求和", Opt(sb), CancellationToken.None);
            var marker = R1Transcript.Marker(res);
            Assert.DoesNotContain("\n", marker, StringComparison.Ordinal);
            Assert.StartsWith("R1_STATS {", marker, StringComparison.Ordinal);
            var json = marker.Substring("R1_STATS ".Length);
            using var doc = JsonDocument.Parse(json);
            Assert.Equal(1, doc.RootElement.GetProperty("calls").GetInt32());
            Assert.Equal(0, doc.RootElement.GetProperty("rc").GetInt32());
        }
        finally
        {
            Directory.Delete(sb, true);
        }
    }

    [Fact]
    public void Role_Mount_Goes_To_User_Turn_Only_Never_Prefix()
    {
        var withRole = R1RoleMount.AppendTo(StructuredPrompt.BuildUserMessage("任务正文"), "角色 seed");
        Assert.Contains("<role_profile>", withRole, StringComparison.Ordinal);
        Assert.DoesNotContain("role_profile", StructuredPrompt.Prefix, StringComparison.Ordinal);
        Assert.Equal(StructuredPrompt.PrefixSha256Pinned, StructuredPrompt.PrefixSha256());
    }
}
