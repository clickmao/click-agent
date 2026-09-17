using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using agent.contract;
using Xunit;

namespace agent.tests;

/// <summary>
/// R536 · R1 契约语义闸（**手写**，不进生成器 ⇒ 重生成不会覆盖）：
///
/// 背景：R535 首次真跑抓到「挂 role 臂两次补全皆 plan=[] ⇒ rc=4 / 0-30」——根因不是 role，
/// 而是契约**自身**有死路分支：`有 missing_slots 或 ambiguities ⇒ plan 必空` 与
/// `intent=code_task ⇒ plan 非空` 同时成立 ⇒「code_task ∧ 任一歧义」在原理上不可满足
/// （校验器 + 准入闸两处都按旧规则判死）。role 里的 `prefer_clarify_first` 只是把模型推上这条死路。
///
/// 本文件钉四件事：
///   ① 差分语料（由 tools/r1gen/contract.py 单一真源生成）逐条裁决一致 ⇒ 两处真源不许静默漂移；
///   ② 前缀 <examples> 里的 <good_response> 必须自己过校验（契约/示例同源自证）；
///   ③ 渲染出的互斥段不得再出现死路条款，且必须出现新优先级（形状判据，配 ① 的内容判据）；
///   ④ 准入闸：多义（有 chosen）不停链、缺信息（missing_slots）才停链。
/// </summary>
public class R1ContractSemanticsTests
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

    private static string FixturePath =>
        Path.Combine(RepoRoot, "src", "agent.tests", "fixtures", "r1-contract-cases.json");

    /// <summary>差分语料路径必须能解析到（缺件 ⇒ 直接红，不静默跳过）。</summary>
    [Fact]
    public void Differential_Fixture_Is_Present_And_Wellformed()
    {
        Assert.True(File.Exists(FixturePath), "缺差分语料: " + FixturePath);
        using var doc = JsonDocument.Parse(File.ReadAllText(FixturePath));
        var cases = doc.RootElement.GetProperty("cases");
        Assert.True(cases.GetArrayLength() >= 10, "语料条数不足: " + cases.GetArrayLength());
    }

    /// <summary>① 逐条差分：Python 规则生成的期望 vs C# 产品校验器实测。</summary>
    [Fact]
    public void Contract_Validator_Agrees_With_Single_Source_Corpus()
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(FixturePath));
        var cases = doc.RootElement.GetProperty("cases");
        var seen = new List<string>();
        foreach (var c in cases.EnumerateArray())
        {
            var name = c.GetProperty("name").GetString() ?? "";
            var body = c.GetProperty("object").GetRawText();
            var expectValid = c.GetProperty("expect_valid").GetBoolean();
            var errs = StructuredContract.Validate(body);

            Assert.Equal(expectValid, errs.Count == 0);
            var joined = string.Join(" | ", errs);
            foreach (var want in c.GetProperty("expect_substrings").EnumerateArray())
            {
                var s = want.GetString() ?? "";
                Assert.True(joined.Contains(s, System.StringComparison.Ordinal),
                    "用例 " + name + " 缺错误子串 「" + s + "」, 实测: " + joined);
            }
            seen.Add(name);
        }
        // 死路反事实控制必须真的在语料里（否则这条闸会被静默删掉而无感）
        Assert.Contains("r535_role_arm_raw_deadend", seen);
        Assert.Contains("r535_shape_after_chosen_and_plan", seen);
    }

    /// <summary>② 前缀示例自证：<good_response> 里的 JSON 必须过校验（负控：改坏一条必红）。</summary>
    [Fact]
    public void Prefix_Good_Responses_Pass_Own_Contract()
    {
        var blocks = GoodResponses(StructuredPrompt.Prefix);
        Assert.True(blocks.Count >= 3, "示例数不足: " + blocks.Count);
        foreach (var b in blocks)
        {
            var errs = StructuredContract.Validate(b);
            Assert.True(errs.Count == 0,
                "前缀示例未过自家契约: " + string.Join(" | ", errs) + " ← " + b.Substring(0, System.Math.Min(80, b.Length)));
        }

        // 负控：把首条示例的 schema_version 改掉 ⇒ 校验必须翻红（证明断言不是空转）
        var mutated = blocks[0].Replace("\"r1.0\"", "\"r9.9\"", System.StringComparison.Ordinal);
        Assert.NotEqual(blocks[0], mutated);
        Assert.NotEmpty(StructuredContract.Validate(mutated));
    }

    /// <summary>③ 形状：死路条款必须消失、新优先级必须在场（配 ① 的内容判据才成立）。</summary>
    [Fact]
    public void Schema_Text_No_Longer_Contains_Unsatisfiable_Rule_Pair()
    {
        var text = StructuredContract.SchemaText;
        Assert.DoesNotContain("有 missing_slots 或 ambiguities ⇒ plan 必空", text, System.StringComparison.Ordinal);
        Assert.Contains("ambiguities **不阻塞**", text, System.StringComparison.Ordinal);
        Assert.Contains("子字段必填: span, issue, options, chosen", text, System.StringComparison.Ordinal);
        // 前缀里也要逐字同源（渲染段是前缀的一段）
        Assert.Contains("ambiguities **不阻塞**", StructuredPrompt.Prefix, System.StringComparison.Ordinal);
    }

    /// <summary>④ 准入闸：多义+chosen+plan ⇒ 不停链（ready）；缺信息 ⇒ rc=2 停链。</summary>
    [Fact]
    public void Gate_Continues_On_Ambiguity_And_Stops_On_Missing_Slots()
    {
        var sandbox = Path.Combine(Path.GetTempPath(), "r1sem-" + System.Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(sandbox);
        try
        {
            const string ambiguousContinue = "{\"schema_version\":\"r1.0\",\"intent\":\"code_task\",\"confidence\":0.85,"
                + "\"entities\":[],\"constraints\":[],\"missing_slots\":[],\"done_when\":[],\"refusal\":null,"
                + "\"ambiguities\":[{\"span\":\"vm_run\",\"issue\":\"模块名与家族名不一致\","
                + "\"options\":[\"按模块名 vm\",\"按家族名 vm_run\"],\"chosen\":\"按模块名 vm\"}],"
                + "\"plan\":[{\"id\":\"s1\",\"tool\":\"run\",\"args\":{\"cmd\":\"echo hi\"},\"depends_on\":[]}]}";
            var ok = StructuredContract.TryParse(ambiguousContinue, out var errs);
            Assert.True(errs.Count == 0, string.Join(" | ", errs));
            Assert.NotNull(ok);
            var outcome = SemanticsPipeline.Gate(ok!, sandbox);
            Assert.Equal(0, outcome.Rc);
            Assert.False(outcome.Halted);
            Assert.Equal("ready", outcome.Stage);
            Assert.Equal("按模块名 vm", ok!.Ambiguities[0].Chosen);

            const string missingInfo = "{\"schema_version\":\"r1.0\",\"intent\":\"code_task\",\"confidence\":0.85,"
                + "\"entities\":[],\"constraints\":[],\"missing_slots\":[\"缺路径\"],\"ambiguities\":[],"
                + "\"plan\":[],\"done_when\":[],\"refusal\":null}";
            var needInfo = StructuredContract.TryParse(missingInfo, out var errs2);
            Assert.True(errs2.Count == 0, string.Join(" | ", errs2));
            var stopped = SemanticsPipeline.Gate(needInfo!, sandbox);
            Assert.Equal(2, stopped.Rc);
            Assert.True(stopped.Halted);
        }
        finally
        {
            Directory.Delete(sandbox, true);
        }
    }

    private static List<string> GoodResponses(string prefix)
    {
        var list = new List<string>();
        const string open = "<good_response>";
        const string close = "</good_response>";
        var at = 0;
        while (true)
        {
            var i = prefix.IndexOf(open, at, System.StringComparison.Ordinal);
            if (i < 0)
            {
                break;
            }
            var j = prefix.IndexOf(close, i, System.StringComparison.Ordinal);
            if (j < 0)
            {
                break;
            }
            list.Add(prefix.Substring(i + open.Length, j - i - open.Length).Trim());
            at = j + close.Length;
        }
        return list;
    }
}
