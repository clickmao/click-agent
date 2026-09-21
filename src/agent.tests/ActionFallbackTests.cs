using System;
using System.Collections.Generic;
using System.Linq;
using agent.contract;
using agent.r1;
using Xunit;

namespace agent.tests;

/// <summary>
/// R619 · RF0004.2（M3 **第三刀 = 空执行面回退**）：轴 <c>AGENTFRAMEWORK_R1_ACTION_EXEC</c>（默认 off）。
///
/// 钉六件事（正控三态 + 判别性负控 + 两侧皆空边界 + 零回归 + 台账字段）：
///   ① 正控（三态可分）：`mappedSteps==0 ∧ planSteps>0` ⇒ 回退，原因码按**既有台账字段**分为
///      `candidates_absent`（键未到达）/ `accepted_empty`（到达但空数组）/ `unmapped_all`（到达且采纳非空但全不可映射）；
///   ② 判别性负控：**有**可执行节点（`mappedSteps>0`）⇒ **不回退**（防「凡空就退」的恒真退化）；
///   ③ 两侧皆空边界：`planSteps==0` ⇒ **不回退**（维持既有空面出口语义，不回退到空 plan）；
///   ④ 触发契约：`UsePlan` 恰等于 `mappedSteps==0 ∧ planSteps>0`（穷举小网格 ⇒ 无遗漏分支）；
///   ⑤ 零回归：轴关（`ExecSource="plan"`）⇒ Marker/Render **不出现**任何新字段（与旧台账逐字节同）；
///   ⑥ 台账：回退档必落 `exec_fallback` 值 = 原因码；不回退档该字段**不出现**。
/// 本类不读写环境变量 ⇒ 无需与环境类互斥集合。
/// </summary>
public class ActionFallbackTests
{
    private const string Reply = @"{
      ""schema_version"": ""r1.0"", ""intent"": ""code_task"", ""confidence"": 0.9,
      ""entities"": [], ""constraints"": [], ""missing_slots"": [], ""ambiguities"": [],
      ""plan"": [
        {""id"": ""s1"", ""tool"": ""write_file"", ""args"": {""path"": ""a.py"", ""content"": ""x""}, ""depends_on"": []},
        {""id"": ""s2"", ""tool"": ""run"", ""args"": {""cmd"": ""python3 a.py"", ""expect_stdout"": ""OK""}, ""depends_on"": [""s1""]}
      ],
      ""done_when"": [], ""refusal"": null,
      ""action_candidates"": [
        {""id"": ""c1"", ""tool"": ""write_file"", ""args"": {""path"": ""a.py"", ""content"": ""x""}, ""why"": ""落盘""},
        {""id"": ""c4"", ""tool"": ""list_dir"", ""args"": {}, ""why"": ""列目录""}
      ]}";

    private static IReadOnlyList<PlanStep> Plan2()
    {
        return new List<PlanStep>
        {
            new("s1", "write_file", "a.py", "x", string.Empty, string.Empty, Array.Empty<string>()),
            new("s2", "run", string.Empty, string.Empty, "python3 a.py", "OK", Array.Empty<string>()),
        };
    }

    private static R1RunResult Base() =>
        new(0, "done", "r", "reply", R1CallStats.Empty, 1, "p", "t", null, 0, null,
            new List<StepOutcome>());

    private static R1Options Opt() => new("/tmp", 1, 30, null, null, "t");

    // ① 正控（三态可分）
    [Fact]
    public void 正控_键未到达_回退plan且原因码为缺席()
    {
        var f = ActionExecPlan.Decide(0, 10, candidatesPresent: false, accepted: 0);
        Assert.Equal("plan_fallback", f.Source);
        Assert.Equal("candidates_absent", f.Fallback);
        Assert.True(f.UsePlan);
    }

    [Fact]
    public void 正控_键到达但空数组_回退且原因码为采纳面空()
    {
        var f = ActionExecPlan.Decide(0, 10, candidatesPresent: true, accepted: 0);
        Assert.Equal("plan_fallback", f.Source);
        Assert.Equal("accepted_empty", f.Fallback);
        Assert.True(f.UsePlan);
    }

    [Fact]
    public void 正控_到达且采纳非空但全不可映射_回退且原因码为全未映射()
    {
        var f = ActionExecPlan.Decide(0, 10, candidatesPresent: true, accepted: 3);
        Assert.Equal("plan_fallback", f.Source);
        Assert.Equal("unmapped_all", f.Fallback);
        Assert.True(f.UsePlan);
    }

    // ② 判别性负控: 有可执行节点 ⇒ 绝不回退
    [Fact]
    public void 判别力负控_有可执行节点则不回退()
    {
        var f = ActionExecPlan.Decide(2, 10, candidatesPresent: true, accepted: 5);
        Assert.Equal("candidates", f.Source);
        Assert.Equal(string.Empty, f.Fallback);
        Assert.False(f.UsePlan);
    }

    // ③ 两侧皆空边界: 不回退（维持既有空面出口）
    [Fact]
    public void 边界_两侧皆空则不回退()
    {
        var f = ActionExecPlan.Decide(0, 0, candidatesPresent: false, accepted: 0);
        Assert.Equal("candidates", f.Source);
        Assert.Equal(string.Empty, f.Fallback);
        Assert.False(f.UsePlan);
    }

    // ④ 触发契约: UsePlan ⇔ (mapped==0 ∧ plan>0)，穷举小网格
    [Fact]
    public void 触发契约_穷举网格_UsePlan恰等于可执行面空且plan非空()
    {
        int[] counts = { 0, 1, 2 };
        int[] accepted = { 0, 1, 3 };
        bool[] present = { false, true };
        var sawFallback = false;
        var sawCandidate = false;
        foreach (var m in counts)
        {
            foreach (var p in counts)
            {
                foreach (var a in accepted)
                {
                    foreach (var pr in present)
                    {
                        var f = ActionExecPlan.Decide(m, p, pr, a);
                        Assert.Equal(m == 0 && p > 0, f.UsePlan);
                        if (f.UsePlan)
                        {
                            sawFallback = true;
                            Assert.Equal("plan_fallback", f.Source);
                            Assert.NotEqual(string.Empty, f.Fallback);
                        }
                        else
                        {
                            sawCandidate = true;
                            Assert.Equal("candidates", f.Source);
                            Assert.Equal(string.Empty, f.Fallback);
                        }
                    }
                }
            }
        }
        Assert.True(sawFallback);
        Assert.True(sawCandidate);
    }

    // ④b 真装配: 用映射器真实产物驱动判定（判据绑组件真实行为，不手填数字）
    [Fact]
    public void 真装配_映射器产物驱动判定_空采纳时回退()
    {
        var sel = ActionCandidates.Select(Reply);
        Assert.NotNull(sel.AcceptedActions);
        var plan = Plan2();
        var mapped = ActionExecPlan.Build(sel.AcceptedActions, plan);
        Assert.True(mapped.Steps.Count > 0);
        Assert.False(ActionExecPlan.Decide(mapped.Steps.Count, plan.Count, sel.Present, sel.Accepted).UsePlan);

        // 空采纳面（键未到达） ⇒ 回退
        var empty = ActionCandidates.Select("{\"intent\":\"code_task\",\"plan\":[]}");
        var mappedEmpty = ActionExecPlan.Build(empty.AcceptedActions, plan);
        Assert.Equal(0, mappedEmpty.Steps.Count);
        Assert.True(ActionExecPlan.Decide(mappedEmpty.Steps.Count, plan.Count, empty.Present, empty.Accepted).UsePlan);
    }

    // ⑤ 零回归: 轴关 ⇒ 新旧字段一律不出现
    [Fact]
    public void 零回归_轴关台账不出现执行面字段()
    {
        var off = Base();
        Assert.DoesNotContain("exec_source", R1Transcript.Marker(off));
        Assert.DoesNotContain("exec_fallback", R1Transcript.Marker(off));
        Assert.DoesNotContain("exec_source", R1Transcript.Render(off, Opt(), "task"));
        Assert.DoesNotContain("exec_fallback", R1Transcript.Render(off, Opt(), "task"));
    }

    // ⑥ 台账: 回退档落原因码; 不回退档该字段不出现
    [Fact]
    public void 台账_回退档落原因码_不回退档字段不出现()
    {
        var fb = Base() with { ExecSource = "plan_fallback", ExecFallback = "candidates_absent" };
        var mk = R1Transcript.Marker(fb);
        Assert.Contains("\"exec_source\":\"plan_fallback\"", mk);
        Assert.Contains("\"exec_fallback\":\"candidates_absent\"", mk);
        var rd = R1Transcript.Render(fb, Opt(), "task");
        Assert.Contains("\"exec_source\": \"plan_fallback\"", rd);
        Assert.Contains("\"exec_fallback\": \"candidates_absent\"", rd);

        var cand = Base() with { ExecSource = "candidates", ActionCandidatesExecuted = 3 };
        Assert.Contains("\"exec_source\":\"candidates\"", R1Transcript.Marker(cand));
        Assert.DoesNotContain("exec_fallback", R1Transcript.Marker(cand));
        Assert.DoesNotContain("exec_fallback", R1Transcript.Render(cand, Opt(), "task"));
    }

    // ⑥b 三态 Source 全域封闭（防新增第四态而无人知）
    [Fact]
    public void Source取值封闭于三态()
    {
        var seen = new SortedSet<string>();
        int[] counts = { 0, 1 };
        bool[] present = { false, true };
        foreach (var m in counts)
        {
            foreach (var p in counts)
            {
                foreach (var a in counts)
                {
                    foreach (var pr in present)
                    {
                        seen.Add(ActionExecPlan.Decide(m, p, pr, a).Source);
                    }
                }
            }
        }
        Assert.Equal(new[] { "candidates", "plan_fallback" }, seen.ToArray());
    }
}
