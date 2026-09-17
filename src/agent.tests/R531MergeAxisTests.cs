using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R531: 合批轴 (第 7 条纪律) 的判据表。
/// 靶点 = R521/R525 逐调用取证里最贵的项: 「一条命令一轮 LLM」的往返 (每轮重发 ~15k 前缀)。
/// 轴设计: 合批**缺省关** ⇒ 注入文本与 R528 逐字节相同 (保形, 可作单变量臂);
///        开 ⇒ 追加第 7 条 (第 1–6 条逐字节不变) ⇒ 与「合批关」臂的差异 = 本条全文, 可归因。
/// 可达成性锁: 动作环宿主必须真的支持单步多工具调用 (`foreach (var tc in calls)`),
///             否则第 7 条退化为话术 (有代码行 ≠ 生效的反向形态: 有文本 ≠ 可行)。
/// </summary>
public sealed class R531MergeAxisTests
{
    private const string MergeEnv = "AGENTFRAMEWORK_ACTION_MERGE";

    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !Directory.Exists(Path.Combine(dir.FullName, "src"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return dir!.FullName;
    }

    private static bool OutsideProductSource(string path)
        => path.Split(Path.DirectorySeparatorChar).Any(s => s == "obj" || s == "bin" || s == "agent.tests");

    private static IEnumerable<string> ProductSources(string srcDir)
        => Directory.EnumerateFiles(srcDir, "*.cs", SearchOption.AllDirectories).Where(f => !OutsideProductSource(f));

    private static void WithMerge(string? value, Action f)
    {
        var old = Environment.GetEnvironmentVariable(MergeEnv);
        try { Environment.SetEnvironmentVariable(MergeEnv, value); f(); }
        finally { Environment.SetEnvironmentVariable(MergeEnv, old); }
    }

    private static string ApplyUnder(string? value)
    {
        var old = Environment.GetEnvironmentVariable(MergeEnv);
        try
        {
            Environment.SetEnvironmentVariable(MergeEnv, value);
            return ActionLoopDiscipline.Apply("SYS");
        }
        finally { Environment.SetEnvironmentVariable(MergeEnv, old); }
    }

    [Fact]
    public void MergeAxis_DefaultOff_TextByteIdenticalToR528()
    {
        WithMerge(null, () =>
        {
            Assert.False(ActionLoopDiscipline.IsMergeEnabled(), "缺省必须关 (保形: 未开臂逐字节等于 R528)");
            const string sys = "SYS-合批关-前缀必须逐字节不变";
            Assert.Equal(sys + "\n\n" + ActionLoopDiscipline.Text, ActionLoopDiscipline.Apply(sys));
            Assert.DoesNotContain("一次成型", ActionLoopDiscipline.CurrentText());
        });
    }

    [Fact]
    public void MergeAxis_OnWordsOnly_DefaultIsOff()
    {
        foreach (var off in new[] { "off", "OFF", "0", "false", " no ", "2" })
            WithMerge(off, () => Assert.False(ActionLoopDiscipline.IsMergeEnabled(), $"词形 {off} 应判关"));
        foreach (var on in new[] { "on", "ON", "1", "true", "True", " yes " })
            WithMerge(on, () => Assert.True(ActionLoopDiscipline.IsMergeEnabled(), $"词形 {on} 应判开"));
    }

    [Fact]
    public void MergeAxis_On_AppendsItem7_PreservingItems1To6ByteWise()
    {
        WithMerge("on", () =>
        {
            var t = ActionLoopDiscipline.CurrentText();
            Assert.StartsWith(ActionLoopDiscipline.Text, t, StringComparison.Ordinal); // 1–6 条逐字节不变
            Assert.Equal(ActionLoopDiscipline.Text + ActionLoopDiscipline.MergeText, t);
            Assert.Contains("7. 一次成型", t);
            Assert.Contains("同一步", t);            // 指向可执行形态, 非话术
            Assert.Contains("工具调用", t);
            Assert.Equal(t.Length - ActionLoopDiscipline.Text.Length, ActionLoopDiscipline.MergeText.Length);
        });
    }

    [Fact]
    public void BothArms_AppendAtTail_PrefixMonotoneInLoop()
    {
        const string sys = "SYS";
        foreach (var arm in new string?[] { null, "on" })
        {
            var first = ApplyUnder(arm);
            var second = ApplyUnder(arm);
            var third = ApplyUnder(arm);
            Assert.StartsWith(sys, first, StringComparison.Ordinal);
            Assert.Equal(first, second);   // 环内各步逐字节相同 ⇒ 前缀单调, 缓存不被本轴破坏
            Assert.Equal(second, third);
        }
    }

    [Fact]
    public void Lever_IsAchievable_MultiToolCallPerStepExistsInHost()
    {
        var runner = Path.Combine(RepoRoot(), "src", "agent.modelqueue", "ActionLoopRunner.cs");
        Assert.True(File.Exists(runner), $"动作环宿主不在场: {runner}");
        var text = File.ReadAllText(runner);
        Assert.Contains("foreach (var tc in calls)", text);   // 单步多工具调用被真的逐个执行
        Assert.Contains("tool_calls", text);
    }

    [Fact]
    public void Wiring_MergeAxisReadOnlyInsideDiscipline()
    {
        var srcDir = Path.Combine(RepoRoot(), "src");
        var readers = ProductSources(srcDir)
            .Where(f => File.ReadAllLines(f).Any(l => l.Contains("MergeEnvName") || l.Contains("IsMergeEnabled")))
            .Select(f => Path.GetFileName(f))
            .ToList();
        Assert.Equal(new[] { "ActionLoopDiscipline.cs" }, readers);   // 无散读 ⇒ 单点求值
    }
}
