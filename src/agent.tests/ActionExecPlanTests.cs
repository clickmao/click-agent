using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using agent.contract;
using agent.r1;
using Xunit;

namespace agent.tests;

/// <summary>
/// R618 · RF0004.2（M3 第二刀）**采纳候选 ⇒ 执行面**：轴 <c>AGENTFRAMEWORK_R1_ACTION_EXEC</c>（默认 off）。
///
/// 钉六件事（正控 + 判别性负控 + 自述期望继承 + 作用域再判 + 零回归 + 轴解析）：
///   ① 正控：合法采纳候选搬成执行面节点，工具名与参数**逐字**不变；
///   ② 自述期望继承：`plan` 里 (工具, 参数) 逐字相等的节点 ⇒ 继承 `expect_stdout`；**不等则不继承**（负控——
///      防「凡有 plan 就继承」的恒真退化）；
///   ③ 判别力负控：窄腰（write_file/run）之外的声明工具、坏 args ⇒ 进 `Unmapped` 且原因码可见（**不静默丢**）；
///   ④ 作用域：映射**不做**语义判断 ⇒ 越界路径必须仍被执行器**再判一次**挡下（真跑，不看代码）；
///   ⑤ 零回归：轴关（ExecSource="plan"）⇒ Marker 与 Render **不出现**四个新字段（与旧台账逐字节同）；
///   ⑥ 轴解析：缺省 = **关**（未放行的产品分支不动）；`1`/`on`/`true` ⇒ 开；`0`/`off`/`false`/垃圾 ⇒ 关。
///
/// 隔离：本类写**进程级**环境变量 ⇒ 与其它集合不并行（复用 `action-boundary-env` 集合）。
/// </summary>
[Collection("action-boundary-env")]
public class ActionExecPlanTests
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
        {""id"": ""c2"", ""tool"": ""run_command"", ""args"": {""command"": ""python3 a.py""}, ""why"": ""自验""},
        {""id"": ""c3"", ""tool"": ""write_file"", ""args"": {""path"": ""b.py"", ""content"": ""y""}, ""why"": ""另一产物""},
        {""id"": ""c4"", ""tool"": ""list_dir"", ""args"": {}, ""why"": ""列目录""},
        {""id"": ""c5"", ""tool"": ""read_file"", ""args"": {""path"": ""a.py""}, ""why"": ""读回""}
      ]}";

    private static IReadOnlyList<PlanStep> Plan()
    {
        var sel = ActionCandidates.Select(Reply);
        Assert.NotNull(sel.AcceptedActions);
        return new List<PlanStep>
        {
            new("s1", "write_file", "a.py", "x", string.Empty, string.Empty, Array.Empty<string>()),
            new("s2", "run", string.Empty, string.Empty, "python3 a.py", "OK", Array.Empty<string>()),
        };
    }

    private static ActionExecPlan.Mapping Map()
    {
        return ActionExecPlan.Build(ActionCandidates.Select(Reply).AcceptedActions, Plan());
    }

    [Fact]
    public void 正控_采纳候选搬成执行面节点且参数逐字不变()
    {
        var m = Map();
        // 5 条采纳里 3 条落在窄腰（c1/c2/c3），2 条无执行面节点（c4/c5）⇒ 缺项可见。
        Assert.Equal(3, m.Steps.Count);
        Assert.Equal(2, m.Unmapped);
        Assert.Equal(new[] { "c1", "c2", "c3" }, new List<string> { m.Steps[0].Id, m.Steps[1].Id, m.Steps[2].Id });
        Assert.Equal("write_file", m.Steps[0].Tool);
        Assert.Equal("a.py", m.Steps[0].Path);
        Assert.Equal("x", m.Steps[0].Content);
        Assert.Equal("run", m.Steps[1].Tool);
        Assert.Equal("python3 a.py", m.Steps[1].Cmd);
    }

    [Fact]
    public void 自述期望_按工具与参数逐字相等继承()
    {
        var m = Map();
        // c1 (write_file, a.py) 与 plan s1 同键同值但 s1 无 expect_stdout ⇒ 不继承；
        // c2 (run, python3 a.py) 与 plan s2 逐字相等 ⇒ 继承 "OK"。
        Assert.Equal("", m.Steps[0].ExpectStdout);
        Assert.Equal("OK", m.Steps[1].ExpectStdout);
        Assert.Equal(1, m.ExpectInherited);
    }

    [Fact]
    public void 负控_期望值不等则不继承()
    {
        var plan = new List<PlanStep>
        {
            new("s9", "run", string.Empty, string.Empty, "python3 OTHER.py", "OK", Array.Empty<string>()),
        };
        var m = ActionExecPlan.Build(ActionCandidates.Select(Reply).AcceptedActions, plan);
        var run = m.Steps[1];
        Assert.Equal("", run.ExpectStdout);
        Assert.Equal(0, m.ExpectInherited);
    }

    [Fact]
    public void 判别力负控_窄腰之外的工具单列不静默丢()
    {
        var m = Map();
        Assert.Contains("no_exec_face:list_dir", m.Reasons);
        Assert.Contains("no_exec_face:read_file", m.Reasons);
        Assert.DoesNotContain(m.Steps, s => s.Id == "c4" || s.Id == "c5");
    }

    [Fact]
    public void 判别力负控_坏参数逐条可见()
    {
        var bad = new List<AcceptedAction>
        {
            new("b1", "write_file", "{not json", "坏 args"),
            new("b2", "write_file", "{\"content\":\"x\"}", "缺 path"),
            new("b3", "run_command", "{\"timeout_ms\":5}", "缺 command"),
            new("b4", "write_file", "[]", "args 非对象"),
        };
        var m = ActionExecPlan.Build(bad, Plan());
        Assert.Equal(0, m.Steps.Count);
        Assert.Equal(4, m.Unmapped);
        Assert.Contains("args_not_json:b1", m.Reasons);
        Assert.Contains("write_file_missing_arg:b2", m.Reasons);
        Assert.Contains("run_command_missing_arg:b3", m.Reasons);
        Assert.Contains("args_not_object:b4", m.Reasons);
    }

    [Fact]
    public void 空输入返回空映射而非空引用()
    {
        Assert.Empty(ActionExecPlan.Build(null, Plan()).Steps);
        Assert.Empty(ActionExecPlan.Build(new List<AcceptedAction>(), Plan()).Steps);
        Assert.Empty(ActionExecPlan.Empty.Steps);
        Assert.Empty(ActionCandidates.Empty.AcceptedActions!);
    }

    [Fact]
    public async Task 作用域_映射不绕过执行器再判_越界必拒_区内照常()
    {
        var root = Path.Combine(Path.GetTempPath(), "r618-execplan-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try
        {
            var opt = new R1Options(root, 1, 30, null, null, "test", 1, false, 0, 0, true);
            // 越界（映射只搬字节，不做语义判断 ⇒ 挡在闸/执行器一侧）
            var escape = new List<PlanStep>
            {
                new("e1", "write_file", "../escape.py", "x", string.Empty, string.Empty, Array.Empty<string>()),
            };
            var r1 = await PlanExecutor.RunAsync(escape, opt, CancellationToken.None);
            Assert.Equal(4, r1.Rc);
            Assert.Equal("scope", r1.Stage);
            Assert.False(File.Exists(Path.Combine(Path.GetDirectoryName(root)!, "escape.py")));

            // 区内照常（防「一刀切全拒」也能骗过上面一条）: 写盘步必须真的落盘；
            //   c2 的 run 会在盘上执行 a.py（内容 "x" 非法）⇒ 执行器在**该步**即早退 ⇒ rc=5 属预期
            //   （自述期望 "OK" 未达成）；故 c3 的 b.py 不在盘上 —— 早退语义一并钉住。
            var inside = ActionExecPlan.Build(ActionCandidates.Select(Reply).AcceptedActions, Plan());
            var r2 = await PlanExecutor.RunAsync(inside.Steps, opt, CancellationToken.None);
            Assert.Equal(5, r2.Rc);
            Assert.True(File.Exists(Path.Combine(root, "a.py")));
            Assert.False(File.Exists(Path.Combine(root, "b.py")));

            // 只搬写盘类候选（无早退）⇒ 两条都必须在盘 ⇒ 「映射不绕过执行器」的反面控制（区内不误拒）。
            var writesOnly = new List<AcceptedAction>
            {
                new("c1", "write_file", "{\"path\":\"a.py\",\"content\":\"x\"}", "落盘"),
                new("c3", "write_file", "{\"path\":\"b.py\",\"content\":\"y\"}", "另一产物"),
            };
            var r3 = await PlanExecutor.RunAsync(ActionExecPlan.Build(writesOnly, Plan()).Steps, opt, CancellationToken.None);
            Assert.Equal(0, r3.Rc);
            Assert.True(File.Exists(Path.Combine(root, "b.py")));
        }
        finally
        {
            try { Directory.Delete(root, true); } catch (IOException) { }
        }
    }

    [Fact]
    public void 轴解析_缺省关_显式开才开()
    {
        var old = Environment.GetEnvironmentVariable(ActionExecPlan.EnvKey);
        try
        {
            Environment.SetEnvironmentVariable(ActionExecPlan.EnvKey, null);
            Assert.False(ActionExecPlan.IsEnabled());          // 缺省 = 关（未放行的产品分支不动）
            Environment.SetEnvironmentVariable(ActionExecPlan.EnvKey, "1");
            Assert.True(ActionExecPlan.IsEnabled());
            Environment.SetEnvironmentVariable(ActionExecPlan.EnvKey, "on");
            Assert.True(ActionExecPlan.IsEnabled());
            Environment.SetEnvironmentVariable(ActionExecPlan.EnvKey, "true");
            Assert.True(ActionExecPlan.IsEnabled());
            Environment.SetEnvironmentVariable(ActionExecPlan.EnvKey, "0");
            Assert.False(ActionExecPlan.IsEnabled());
            Environment.SetEnvironmentVariable(ActionExecPlan.EnvKey, "off");
            Assert.False(ActionExecPlan.IsEnabled());
            Environment.SetEnvironmentVariable(ActionExecPlan.EnvKey, "false");
            Assert.False(ActionExecPlan.IsEnabled());
            Environment.SetEnvironmentVariable(ActionExecPlan.EnvKey, "垃圾值");
            Assert.False(ActionExecPlan.IsEnabled());
        }
        finally
        {
            Environment.SetEnvironmentVariable(ActionExecPlan.EnvKey, old);
        }
    }

    [Fact]
    public void 零回归_轴关台账不出现新字段_轴开逐字段落()
    {
        var planOnly = new R1RunResult(0, "done", "r", "reply", R1CallStats.Empty, 1, "p", "t", null, 0, null,
            new List<StepOutcome>());
        var markerOff = R1Transcript.Marker(planOnly);
        var renderOff = R1Transcript.Render(planOnly, new R1Options("/tmp", 1, 30, null, null, "t"), "task");
        Assert.DoesNotContain("exec_source", markerOff);
        Assert.DoesNotContain("action_candidates_executed", markerOff);
        Assert.DoesNotContain("exec_source", renderOff);

        var on = planOnly with
        {
            ExecSource = "candidates",
            ActionCandidatesExecuted = 3,
            ActionCandidatesUnmapped = 2,
            ActionCandidatesExpectInherited = 1,
        };
        var markerOn = R1Transcript.Marker(on);
        Assert.Contains("\"exec_source\":\"candidates\"", markerOn);
        Assert.Contains("\"action_candidates_executed\":3", markerOn);
        Assert.Contains("\"action_candidates_unmapped\":2", markerOn);
        Assert.Contains("\"action_candidates_expect_inherited\":1", markerOn);
        Assert.Contains("\"exec_source\": \"candidates\"", R1Transcript.Render(on, new R1Options("/tmp", 1, 30, null, null, "t"), "task"));
    }
}
