using System;
using System.Collections.Generic;
using System.Text.Json;
using agent.modelqueue;
using agent.r1;
using Xunit;

namespace agent.tests;

/// <summary>
/// R610 · RF0004.2（M3 第一刀）**动作候选**：契约面声明 + 本地机械裁选 + 台账三字段。
///
/// 钉六件事（正控 + 判别性负控 + 同源闸 + 零回归 + 边界 + 轴解析）：
///   ① 正控：合法候选被采纳（声明/采纳/拒绝三计数一致）；
///   ② 负控（判别力）：**未声明工具** / 重复 id / 缺 why / args 缺必填 ⇒ 各自进拒绝并给**可机检原因码**
///      （不是「跑了 N 条」而是「判定了 N 条」—— 恒绿的空心判据在此翻红）；
///   ③ 同源闸：工具白名单**取执行面** `ActionToolDecl.Names`；契约面渲染出的枚举必须与它**逐名同序**
///      （任一改工具面而忘改契约渲染 ⇒ 本测红）；
///   ④ 零回归：声明数 = 0（含轴关）⇒ 台账/Marker **不出现**三个字段（字段缺席即旧行为）；
///   ⑤ 边界：非 JSON 回复 / 无该字段 / 空回复 ⇒ 声明数 0（不作判据，不抛）；
///   ⑥ 轴解析：缺省 = 开；`0`/`off`/`false` ⇒ 关；其余（含 `on`/垃圾值）= 开。
/// </summary>
public class ActionCandidatesTests
{
    private const string ValidReply = @"{
      ""schema_version"": ""r1.0"", ""intent"": ""code_task"", ""confidence"": 0.9,
      ""entities"": [], ""constraints"": [], ""missing_slots"": [], ""ambiguities"": [],
      ""plan"": [{""id"": ""s1"", ""tool"": ""write_file"", ""args"": {""path"": ""a.py"", ""content"": ""x""}, ""depends_on"": []}],
      ""done_when"": [], ""refusal"": null,
      ""action_candidates"": [
        {""id"": ""c1"", ""tool"": ""write_file"", ""args"": {""path"": ""a.py"", ""content"": ""x""}, ""why"": ""落盘产物""},
        {""id"": ""c2"", ""tool"": ""run_command"", ""args"": {""command"": ""python3 a.py""}, ""why"": ""自验""},
        {""id"": ""c3"", ""tool"": ""list_dir"", ""args"": {}, ""why"": ""列目录（无必填参数）""}
      ]}";

    [Fact]
    public void 正控_合法候选逐条采纳()
    {
        var sel = ActionCandidates.Select(ValidReply);
        Assert.Equal(3, sel.Declared);
        Assert.Equal(3, sel.Accepted);
        Assert.Equal(0, sel.Rejected);
        Assert.Equal(new[] { "c1", "c2", "c3" }, sel.AcceptedIds);
    }

    [Fact]
    public void 负控_四类非法各自可机检拒绝()
    {
        var reply = @"{
          ""action_candidates"": [
            {""id"": ""ok"", ""tool"": ""read_file"", ""args"": {""path"": ""a.py""}, ""why"": ""读""},
            {""id"": ""bad-tool"", ""tool"": ""shell_exec"", ""args"": {}, ""why"": ""未声明的工具""},
            {""id"": ""ok"", ""tool"": ""list_dir"", ""args"": {}, ""why"": ""重复 id""},
            {""id"": ""no-why"", ""tool"": ""list_dir"", ""args"": {}},
            {""id"": ""no-args"", ""tool"": ""write_file"", ""args"": {""path"": ""a.py""}, ""why"": ""缺 content""},
            {""id"": ""args-not-obj"", ""tool"": ""run_command"", ""args"": ""x"", ""why"": ""args 形态错""}
          ]}";
        var sel = ActionCandidates.Select(reply);
        Assert.Equal(6, sel.Declared);
        Assert.Equal(1, sel.Accepted);
        Assert.Equal(5, sel.Rejected);
        Assert.Contains("tool_not_declared:shell_exec", sel.RejectReasons);
        Assert.Contains("duplicate_id:ok", sel.RejectReasons);
        Assert.Contains("missing_field", sel.RejectReasons);
        Assert.Contains("args_missing_required:write_file", sel.RejectReasons);
        Assert.Contains("args_not_object", sel.RejectReasons);
        // 拒绝原因数 == 拒绝数（每个拒绝项恰一条原因 ⇒ 不是「计数即结论」的空心面）
        Assert.Equal(sel.Rejected, sel.RejectReasons.Count);
    }

    [Fact]
    public void 同源闸_白名单取执行面且契约枚举逐名同序()
    {
        Assert.Equal(5, ActionToolDecl.Names.Length);
        foreach (var n in ActionToolDecl.Names)
        {
            Assert.True(ActionToolDecl.IsDeclared(n));
        }
        // 契约面渲染的枚举必须与执行面**逐名同序**（改一处不改另一处 ⇒ 本测红）
        var rendered = "tool ∈ " + string.Join("|", ActionToolDecl.Names);
        Assert.Contains(rendered, agent.contract.StructuredPrompt.Prefix);
        // 必填参数键由声明面自身的 JSON Schema 派生（禁另立表）
        Assert.Equal(new[] { "path", "content" }, ActionCandidates.RequiredArgsOf(ActionToolDecl.WriteFile));
        Assert.Equal(new[] { "command" }, ActionCandidates.RequiredArgsOf(ActionToolDecl.RunCommand));
        Assert.Empty(ActionCandidates.RequiredArgsOf(ActionToolDecl.ListDir));
    }

    [Fact]
    public void 零回归_声明数为零时台账字段缺席()
    {
        var r0 = Result(0, 0, 0);
        var m0 = R1Transcript.Marker(r0);
        Assert.DoesNotContain("action_candidates", m0);
        var t0 = R1Transcript.Render(r0, Opt(), "task");
        Assert.DoesNotContain("action_candidates", t0);

        var r1 = Result(3, 3, 0);
        var m1 = R1Transcript.Marker(r1);
        using (var doc = JsonDocument.Parse(m1.Substring("R1_STATS ".Length)))
        {
            Assert.Equal(3, doc.RootElement.GetProperty("action_candidates_declared").GetInt32());
            Assert.Equal(3, doc.RootElement.GetProperty("action_candidates_accepted").GetInt32());
            Assert.Equal(0, doc.RootElement.GetProperty("action_candidates_rejected").GetInt32());
        }
    }

    [Fact]
    public void 边界_非JSON与缺字段与空回复恒零()
    {
        Assert.Equal(0, ActionCandidates.Select("").Declared);
        Assert.Equal(0, ActionCandidates.Select("not json").Declared);
        Assert.Equal(0, ActionCandidates.Select(@"{""intent"":""question""}").Declared);
        Assert.Equal(0, ActionCandidates.Select(@"{""action_candidates"": {}}").Declared);
    }

    [Fact]
    public void 轴解析_缺省开且显式关()
    {
        var key = ActionCandidates.EnvKey;
        var old = Environment.GetEnvironmentVariable(key);
        try
        {
            Environment.SetEnvironmentVariable(key, null);
            Assert.True(ActionCandidates.IsEnabled());
            Environment.SetEnvironmentVariable(key, "off");
            Assert.False(ActionCandidates.IsEnabled());
            Environment.SetEnvironmentVariable(key, "0");
            Assert.False(ActionCandidates.IsEnabled());
            Environment.SetEnvironmentVariable(key, "false");
            Assert.False(ActionCandidates.IsEnabled());
            Environment.SetEnvironmentVariable(key, "on");
            Assert.True(ActionCandidates.IsEnabled());
        }
        finally
        {
            Environment.SetEnvironmentVariable(key, old);
        }
    }

    private static R1RunResult Result(int declared, int accepted, int rejected) =>
        new(0, "done", "reason", "raw", R1CallStats.Empty, 15697, "sha", "tsha", null, 0, null,
            new List<StepOutcome>(),
            ActionCandidatesDeclared: declared, ActionCandidatesAccepted: accepted,
            ActionCandidatesRejected: rejected);

    private static R1Options Opt() =>
        new("/tmp/r610test", 1, 120, null, null, "r610test");
}
