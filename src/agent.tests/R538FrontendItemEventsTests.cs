using System.Text.Json;
using agent.frontendapi;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R538: 前端条目面 (item.*) 的派生规则与载荷形状 —— 对标 codex 展示面 §4.3。
/// 覆盖: kind 由工具名派生 (单源 ActionToolDecl) / title 主参数 / 参数坏 JSON 不伪造 /
/// 输出尾裁剪 (留尾不留头) / 行数全量 / 截断标记 / item_id 兜底 / 载荷字段完整性。
/// </summary>
public sealed class R538FrontendItemEventsTests
{
    // ---------- (1) kind 派生 (单源: ActionToolDecl 常量, 不复制工具语义表) ----------

    [Theory]
    [InlineData(ActionToolDecl.RunCommand, "command")]
    [InlineData(ActionToolDecl.WriteFile, "file_write")]
    [InlineData(ActionToolDecl.ReadFile, "file_read")]
    [InlineData(ActionToolDecl.DeleteFile, "file_delete")]
    [InlineData(ActionToolDecl.ListDir, "listing")]
    [InlineData("no_such_tool", "other")]
    [InlineData("", "other")]
    public void Kind_IsDerivedFromToolName(string tool, string expected)
        => Assert.Equal(expected, ActionItemText.KindOf(tool));

    // ---------- (2) title / detail ----------

    [Fact]
    public void Title_UsesPrimaryArgument()
    {
        var (kind, title, detail) = ActionItemText.Describe(
            ActionToolDecl.RunCommand, "{\"command\":\"cat a.txt\"}");
        Assert.Equal("command", kind);
        Assert.Equal("run_command cat a.txt", title);
        Assert.Equal("{\"command\":\"cat a.txt\"}", detail);

        var (_, wTitle, _) = ActionItemText.Describe(
            ActionToolDecl.WriteFile, "{\"path\":\"dir/x.py\",\"content\":\"print(1)\"}");
        Assert.Equal("write_file dir/x.py", wTitle);

        var (_, lTitle, _) = ActionItemText.Describe(ActionToolDecl.ListDir, "{\"path\":\"src\"}");
        Assert.Equal("list_dir src", lTitle);
    }

    /// <summary>
    /// R538 同源机检: 主参数键**只能**来自 ActionToolSpec 的 schema (required[0]) ——
    /// 若某天工具改名/换参数键, 这里必红, 而不是让 title 静默丢参数 (本轮真跑曾因此在 run_command 上丢过命令体)。
    /// </summary>
    [Fact]
    public void PrimaryArgKey_IsWiredToEveryDeclaredTool()
    {
        foreach (var spec in ActionToolSpec.All)
        {
            var key = ActionToolSpec.PrimaryArgKey(spec.Name);
            Assert.False(string.IsNullOrWhiteSpace(key), spec.Name + " 的 schema 没有 required/properties ⇒ 标题会退化成纯工具名");
            var (_, title, _) = ActionItemText.Describe(spec.Name, "{\"" + key + "\":\"X9\"}");
            Assert.EndsWith(" X9", title);
        }
        Assert.Equal(string.Empty, ActionToolSpec.PrimaryArgKey("no_such_tool"));
    }

    [Fact]
    public void BadOrMissingArguments_DoNotFabricateTitle()
    {
        var (_, broken, _) = ActionItemText.Describe(ActionToolDecl.RunCommand, "{not json");
        Assert.Equal("run_command", broken);                  // 解析失败 ⇒ 只留工具名 (不猜参数)

        var (_, empty, _) = ActionItemText.Describe(ActionToolDecl.RunCommand, null);
        Assert.Equal("run_command", empty);

        var (_, scalar, _) = ActionItemText.Describe(ActionToolDecl.RunCommand, "{\"command\":123}");
        Assert.Equal("run_command 123", scalar);              // 非字符串标量按原样 (不静默丢弃)
    }

    [Fact]
    public void Detail_IsCapped_WithSuffix()
    {
        var big = "{\"command\":\"" + new string('x', ActionItemText.DetailCharCap + 50) + "\"}";
        var (_, _, detail) = ActionItemText.Describe(ActionToolDecl.RunCommand, big);
        Assert.True(detail.Length < big.Length);
        Assert.EndsWith("...[truncated]", detail);
    }

    [Fact]
    public void Title_IsCapped()
    {
        var (_, title, _) = ActionItemText.Describe(
            ActionToolDecl.RunCommand, "{\"command\":\"" + new string('y', ActionItemText.TitleCharCap + 10) + "\"}");
        Assert.EndsWith("...[truncated]", title);
    }

    // ---------- (3) 输出尾裁剪 ----------

    [Fact]
    public void Tail_KeepsTheEnd_AndCountsAllLines()
    {
        var body = string.Join("\n", Enumerable.Range(1, 400).Select(i => "line-" + i));
        var (tail, lines, truncated) = ActionItemText.Tail(body);
        Assert.Equal(400, lines);                              // 行数是全量事实
        Assert.True(truncated);
        Assert.Equal(ActionItemText.OutputTailCharCap, tail.Length);
        Assert.EndsWith("line-400", tail);                     // 留尾: 结论在最后
        Assert.DoesNotContain("line-1\n", tail);
    }

    [Fact]
    public void Tail_SmallOutputIsUntouched()
    {
        var (tail, lines, truncated) = ActionItemText.Tail("ok\nwarn\ndone");
        Assert.Equal("ok\nwarn\ndone", tail);
        Assert.Equal(3, lines);
        Assert.False(truncated);
    }

    [Fact]
    public void Tail_EmptyOutput_IsZeroLines_NotOne()
        => Assert.Equal((string.Empty, 0, false), ActionItemText.Tail(null));

    /// <summary>尾换行不是内容行 (真跑里 `cat` 输出 "ok\n" 曾被数成 2 行 ⇒ 前端会多显示一个空行)。</summary>
    [Fact]
    public void Tail_TrailingNewline_IsNotAnExtraLine()
    {
        Assert.Equal(1, ActionItemText.Tail("ok\n").LinesTotal);
        Assert.Equal(2, ActionItemText.Tail("a\nb\n").LinesTotal);
        Assert.Equal(0, ActionItemText.Tail("").LinesTotal);
    }

    // ---------- (4) item_id 配对兜底 ----------

    [Fact]
    public void ItemId_FallsBackToStepIndex()
    {
        Assert.Equal("c1", ActionItemText.ItemIdOf("c1", 3));
        Assert.Equal("item-3", ActionItemText.ItemIdOf(null, 3));
        Assert.Equal("item-3", ActionItemText.ItemIdOf("   ", 3));
    }

    // ---------- (5) 载荷形状 (前端契约面: 字段齐、无反射、可解析) ----------

    [Fact]
    public void ItemJson_HasAllContractFields()
    {
        var reg = new FrontendTaskRegistry();
        var taskId = reg.Start("s1", "chat.send");
        var json = reg.ItemJson(taskId, "c1", "completed", "command", "run_command cat a.txt",
            "{\"command\":\"cat a.txt\"}", "hello", 2, true, 1, 42);
        using var d = JsonDocument.Parse(json);
        var r = d.RootElement;
        Assert.Equal(taskId, r.GetProperty("task_id").GetString());
        Assert.Equal("c1", r.GetProperty("item_id").GetString());
        Assert.Equal("completed", r.GetProperty("phase").GetString());
        Assert.Equal("command", r.GetProperty("kind").GetString());
        Assert.Equal("run_command cat a.txt", r.GetProperty("title").GetString());
        Assert.Equal("{\"command\":\"cat a.txt\"}", r.GetProperty("detail").GetString());
        Assert.Equal("hello", r.GetProperty("output_tail").GetString());
        Assert.Equal(2, r.GetProperty("lines_total").GetInt32());
        Assert.True(r.GetProperty("truncated").GetBoolean());
        Assert.Equal(1, r.GetProperty("exit_code").GetInt32());
        Assert.Equal(42, r.GetProperty("elapsed_ms").GetInt64());
        Assert.Equal(11, r.EnumerateObject().Count());          // 字段面无遗漏/无多余
    }

    [Fact]
    public void Snapshot_LastItem_Null_WhenNoItemRecorded()
    {
        var reg = new FrontendTaskRegistry();
        reg.Start("s1", "chat.send");
        using var d = JsonDocument.Parse(reg.SnapshotJson());
        Assert.Equal(JsonValueKind.Null, d.RootElement[0].GetProperty("last_item").ValueKind);
    }
}
