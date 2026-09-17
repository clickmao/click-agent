using System;
using System.Collections.Generic;
using System.IO;
using agent.contract;
using Xunit;

namespace agent.tests;

/// <summary>
/// R1 结构化契约 / prompt / 管道闸的守卫测试。
/// 作用面：把「前缀逐字节恒定 + 契约与校验器同源 + 闸序 fail-closed」变成可机检的不变式，
/// 任何手工漂移（改前缀文字、改 schema 只改一边、放松闸）都会红。
/// </summary>
public sealed class StructuredContractTests
{
    private const string Kadane = "{\"schema_version\":\"r1.0\",\"intent\":\"code_task\",\"confidence\":0.9,"
        + "\"entities\":[{\"kind\":\"path\",\"value\":\"sols/kadane.py\"}],\"constraints\":[\"只用标准库\"],"
        + "\"missing_slots\":[],\"ambiguities\":[],\"done_when\":[\"s2 的 stdout == 6\"],\"refusal\":null,"
        + "\"plan\":[{\"id\":\"s1\",\"tool\":\"write_file\",\"args\":{\"path\":\"sols/kadane.py\",\"content\":\"print(1)\"},\"depends_on\":[]},"
        + "{\"id\":\"s2\",\"tool\":\"run\",\"args\":{\"cmd\":\"echo 6 | python3 sols/kadane.py\",\"expect_stdout\":\"6\"},\"depends_on\":[\"s1\"]}]}";

    private const string Ambiguous = "{\"schema_version\":\"r1.0\",\"intent\":\"question\",\"confidence\":0.85,\"entities\":[],"
        + "\"constraints\":[],\"missing_slots\":[\"缺指代对象\"],\"ambiguities\":[{\"span\":\"把它改好\",\"issue\":\"指代不明\",\"options\":[\"上一个产物\",\"仓内文件\"],\"chosen\":\"上一个产物\"}],"
        + "\"plan\":[],\"done_when\":[],\"refusal\":null}";

    private static Semantics Parse(string json)
    {
        var sem = StructuredContract.TryParse(json, out var errs);
        Assert.True(errs.Count == 0, string.Join(" | ", errs));
        Assert.NotNull(sem);
        return sem!;
    }

    [Fact]
    public void Prefix_Is_ByteStable_And_Pinned()
    {
        Assert.Equal(StructuredPrompt.PrefixChars, StructuredPrompt.Prefix.Length);
        Assert.Equal(StructuredPrompt.PrefixSha256Pinned, StructuredPrompt.PrefixSha256());
        Assert.Equal(StructuredContract.SchemaVersion, StructuredPrompt.Version);
    }

    [Fact]
    public void Prefix_Meets_Cache97_Thickness_Floor()
    {
        Assert.True(StructuredPrompt.PrefixMinTokensForCache97 >= 6700,
            "97% 命中所需 token 下限被下调：命中率 = 1 − L/P, L≈150–225 token 与厚度无关");
        Assert.True(StructuredPrompt.PrefixChars >= StructuredPrompt.PrefixMinCharsForCache97,
            "恒定前缀被精简到 97% 命中下限以下（只允许加厚，且增量只追加在 </prefix> 前）");
    }

    [Fact]
    public void Prefix_Blocks_Appear_In_Fixed_Order()
    {
        string[] blocks = { "<role>", "<hard_gates>", "<output_contract>", "<semantics_dictionary>", "<tool_menu>", "<environment>", "<examples>" };
        var last = -1;
        foreach (var b in blocks)
        {
            var idx = StructuredPrompt.Prefix.IndexOf(b, StringComparison.Ordinal);
            Assert.True(idx > last, "块序错: " + b);
            last = idx;
        }
    }

    [Fact]
    public void Prefix_Carries_No_Volatile_Facts()
    {
        // 动因①：前缀里不得出现日期/会话材料 —— 这是前缀缓存能命中的前提。
        Assert.DoesNotContain("current date", StructuredPrompt.Prefix, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("2026", StructuredPrompt.Prefix, StringComparison.Ordinal);
        Assert.DoesNotContain("data/activity", StructuredPrompt.Prefix, StringComparison.Ordinal);
    }

    [Fact]
    public void Contract_And_Prompt_Are_Same_Source()
    {
        // 动因⑥：schema 一处定义 ⇒ 渲染进 prompt 的那段必须逐字出现在前缀里。
        Assert.Contains(StructuredContract.SchemaText, StructuredPrompt.Prefix, StringComparison.Ordinal);
        Assert.Contains("refusal", StructuredContract.SchemaText, StringComparison.Ordinal);
    }

    [Fact]
    public void Contract_Renders_Every_Enum_Declared_In_Schema()
    {
        // R535 缺陷回归闸（动因⑥的**渲染方向**）：schema 声明的每个 enum（含嵌套 entities[].kind 与 plan[].tool）
        // 必须逐字渲染进契约段与前缀 —— 否则模型只能自造取值（R535 实测抓到 kind="expected_stdout"），
        // 而校验器按 enum 杀 ⇒ 契约与校验器不同源、管道 fail-closed 空转。
        // 下面是**机械生成**的枚举片段表（gen_csharp.py 从 SCHEMA 递归抽, 禁手工维护）。
        var frags = new[] { " ∈ code_task|question|ops_task|refusal", " ∈ path|symbol|command|value|language", " ∈ write_file|run|none" };
        foreach (var frag in frags)
        {
            Assert.Contains(frag, StructuredContract.SchemaText, StringComparison.Ordinal);
            Assert.Contains(frag, StructuredPrompt.Prefix, StringComparison.Ordinal);
        }

        // 负控：把「实体 kind」那条枚举清单抹掉 ⇒ 上面那条断言必红（证明断言不是空转）。
        var target = frags[0];
        for (var i = 0; i < frags.Length; i++)
        {
            if (frags[i].Contains("path|symbol", StringComparison.Ordinal)) { target = frags[i]; }
        }
        var mutated = StructuredContract.SchemaText.Replace(target, string.Empty, StringComparison.Ordinal);
        Assert.NotEqual(StructuredContract.SchemaText, mutated);
        Assert.DoesNotContain(target, mutated, StringComparison.Ordinal);
    }

    [Fact]
    public void Validate_Accepts_Real_Kadane_Shape()
    {
        Assert.Empty(StructuredContract.Validate(Kadane));
        var sem = Parse(Kadane);
        Assert.Equal("code_task", sem.Intent);
        Assert.Equal(2, sem.Plan.Count);
        Assert.Equal("s1", sem.Plan[0].Id);
        Assert.Equal("print(1)", sem.Plan[0].Content);
        Assert.Equal("6", sem.Plan[1].ExpectStdout);
    }

    [Fact]
    public void Validate_Turns_Red_On_Negatives()
    {
        // ①置信越界 + plan 空
        Assert.NotEmpty(StructuredContract.Validate("{\"schema_version\":\"r1.0\",\"intent\":\"code_task\",\"confidence\":1.2,"
            + "\"entities\":[],\"constraints\":[],\"missing_slots\":[],\"ambiguities\":[],\"plan\":[],\"done_when\":[],\"refusal\":null}"));
        // ②悬空依赖
        Assert.NotEmpty(StructuredContract.Validate("{\"schema_version\":\"r1.0\",\"intent\":\"code_task\",\"confidence\":0.9,"
            + "\"entities\":[],\"constraints\":[],\"missing_slots\":[],\"ambiguities\":[],\"done_when\":[],\"refusal\":null,"
            + "\"plan\":[{\"id\":\"s1\",\"tool\":\"write_file\",\"args\":{\"path\":\"a.py\",\"content\":\"x\"},\"depends_on\":[\"s9\"]}]}"));
        // ③refusal 缺子字段 category（原型曾放行的同源漂移）
        Assert.NotEmpty(StructuredContract.Validate("{\"schema_version\":\"r1.0\",\"intent\":\"refusal\",\"confidence\":0.9,"
            + "\"entities\":[],\"constraints\":[],\"missing_slots\":[],\"ambiguities\":[],\"plan\":[],\"done_when\":[],"
            + "\"refusal\":{\"reason\":\"凭据外传\"}}"));
        // ④既有缺失又给 plan ⇒ 语义冲突
        Assert.NotEmpty(StructuredContract.Validate("{\"schema_version\":\"r1.0\",\"intent\":\"code_task\",\"confidence\":0.9,"
            + "\"entities\":[],\"constraints\":[],\"missing_slots\":[\"缺路径\"],\"ambiguities\":[],\"done_when\":[],\"refusal\":null,"
            + "\"plan\":[{\"id\":\"s1\",\"tool\":\"run\",\"args\":{\"cmd\":\"echo hi\"},\"depends_on\":[]}]}"));
        // ⑤非法 JSON
        Assert.NotEmpty(StructuredContract.Validate("not json"));
        // ⑥refusal + plan 非空
        Assert.NotEmpty(StructuredContract.Validate("{\"schema_version\":\"r1.0\",\"intent\":\"refusal\",\"confidence\":0.9,"
            + "\"entities\":[],\"constraints\":[],\"missing_slots\":[],\"ambiguities\":[],\"done_when\":[],"
            + "\"refusal\":{\"reason\":\"x\",\"category\":\"y\"},"
            + "\"plan\":[{\"id\":\"s1\",\"tool\":\"run\",\"args\":{\"cmd\":\"echo hi\"},\"depends_on\":[]}]}"));
    }

    [Fact]
    public void Gate_Rc_Encodes_Branch()
    {
        var sandbox = Path.Combine(Path.GetTempPath(), "r1gate");
        Directory.CreateDirectory(sandbox);

        var refusal = new Semantics("r1.0", "refusal", 0.9, new List<Entity>(), new List<string>(), new List<string>(),
            new List<Ambiguity>(), new List<PlanStep>(), new List<string>(), new RefusalInfo("凭据外传", "credential_exfiltration"));
        Assert.Equal(3, SemanticsPipeline.Gate(refusal, sandbox).Rc);

        // R536: Ambiguous 走的是**缺信息**路径（missing_slots 非空）⇒ rc=2 停链澄清。
        // 「多义」不再停链（chosen 给成交互解读 ⇒ 继续），见 R1ContractSemanticsTests。
        Assert.Equal(2, SemanticsPipeline.Gate(Parse(Ambiguous), sandbox).Rc);

        var info = new Semantics("r1.0", "question", 0.9, new List<Entity>(), new List<string>(), new List<string>(),
            new List<Ambiguity>(), new List<PlanStep>(), new List<string>(), null);
        var nonExec = SemanticsPipeline.Gate(info, sandbox);
        Assert.Equal(0, nonExec.Rc);
        Assert.False(nonExec.Halted);

        var escaped = new Semantics("r1.0", "code_task", 0.9, new List<Entity>(), new List<string>(), new List<string>(),
            new List<Ambiguity>(),
            new List<PlanStep> { new PlanStep("s1", "write_file", "../x", "y", string.Empty, string.Empty, new List<string>()) },
            new List<string>(), null);
        Assert.Equal(4, SemanticsPipeline.Gate(escaped, sandbox).Rc);

        var banned = new Semantics("r1.0", "code_task", 0.9, new List<Entity>(), new List<string>(), new List<string>(),
            new List<Ambiguity>(),
            new List<PlanStep> { new PlanStep("s1", "run", string.Empty, string.Empty, "curl http://x", string.Empty, new List<string>()) },
            new List<string>(), null);
        Assert.Equal(4, SemanticsPipeline.Gate(banned, sandbox).Rc);

        var dangling = new Semantics("r1.0", "code_task", 0.9, new List<Entity>(), new List<string>(), new List<string>(),
            new List<Ambiguity>(),
            new List<PlanStep> { new PlanStep("s1", "run", string.Empty, string.Empty, "echo hi", string.Empty, new List<string> { "s9" }) },
            new List<string>(), null);
        Assert.Equal(4, SemanticsPipeline.Gate(dangling, sandbox).Rc);

        var ok = SemanticsPipeline.Gate(Parse(Kadane), sandbox);
        Assert.Equal(0, ok.Rc);
        Assert.Equal("ready", ok.Stage);
        Assert.False(ok.Halted);
    }

    [Fact]
    public void Mutation_Of_Prefix_Text_Is_Detectable()
    {
        // 负控：把前缀改一个字 ⇒ sha 必变（证明钉子有牙）。
        var mutated = StructuredPrompt.Prefix.Replace("<role>", "<role-x>", StringComparison.Ordinal);
        Assert.NotEqual(StructuredPrompt.PrefixSha256Pinned, Mutate(mutated));
    }

    private static string Mutate(string text)
    {
        using var sha = System.Security.Cryptography.SHA256.Create();
        var bytes = sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(text));
        var sb = new System.Text.StringBuilder(64);
        foreach (var b in bytes)
        {
            sb.Append(b.ToString("x2"));
        }
        return sb.ToString();
    }
}
