using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R522: 动作环上下文纪律的判据表 —— 环境轴 (缺省开/词形关) + 前缀单调 (尾部追加) +
/// 文本锚 (三条纪律) + **结构锁** (注入点必须在动作环分支内, 且全仓唯 1 处调用)。
/// 依据 = R521 逐调用取证: 19 次调用里 20 步用于「一条命令一轮 LLM」, 收尾叙述 16,540 字
/// (同题 codex: 5 次调用 / 3,926 字) ⇒ 靶点是调用粒度与收尾冗余, 不是缓存。
/// </summary>
public sealed class R522ContextDisciplineTests
{
    private const string Env = "AGENTFRAMEWORK_ACTION_DISCIPLINE";

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

    [Fact]
    public void IsEnabled_DefaultOn_OffWordsOnly()
    {
        var old = Environment.GetEnvironmentVariable(Env);
        try
        {
            Environment.SetEnvironmentVariable(Env, null);
            Assert.True(ActionLoopDiscipline.IsEnabled(), "缺省必须开 (本轮改进的缺省态)");
            foreach (var off in new[] { "off", "OFF", "Off", "0", "false", "False", " false " })
            {
                Environment.SetEnvironmentVariable(Env, off);
                Assert.False(ActionLoopDiscipline.IsEnabled(), $"词形 {off} 应判关 (消融臂依赖此轴)");
            }
            foreach (var on in new[] { "on", "1", "true", "yes", "  " })
            {
                Environment.SetEnvironmentVariable(Env, on);
                Assert.True(ActionLoopDiscipline.IsEnabled(), $"词形 {on} 应判开");
            }
        }
        finally
        {
            Environment.SetEnvironmentVariable(Env, old);
        }
    }

    [Fact]
    public void Apply_AppendsToTail_PrefixByteIdentical()
    {
        const string sys = "SYS-前缀-必须逐字节不变";
        var outp = ActionLoopDiscipline.Apply(sys);
        Assert.Equal(sys + "\n\n" + ActionLoopDiscipline.Text, outp);
        Assert.StartsWith(sys, outp, StringComparison.Ordinal);          // 前缀不动 ⇒ 环内缓存前缀单调
        Assert.True(outp.Length > sys.Length + 100, "纪律块必须实际进入请求体");
        Assert.Equal(ActionLoopDiscipline.Text, ActionLoopDiscipline.Apply(""));
    }

    [Fact]
    public void Text_HasThreeDisciplineAnchors()
    {
        var t = ActionLoopDiscipline.Text;
        Assert.Contains("验证合并", t);      // 一次 run_command 跑完全部用例
        Assert.Contains("探针不落盘", t);    // 临时检查内联, 不留临时文件
        Assert.Contains("收尾从简", t);      // 最后一条消息只给结论 + 证据
        Assert.Contains("run_command", t);   // 指向真实工具名 (非话术)
        Assert.Contains("产物落位与自验", t); // R528: 工作根 + 题面相对路径
        Assert.Contains("工作根", t);         // R528: 自验必须在工作根执行 (禁 cd 到子目录)
    }

    [Fact]
    public void Wiring_SitsInsideActionLoopBranch_AndIsUnique()
    {
        var srcDir = Path.Combine(RepoRoot(), "src");
        var adapter = Path.Combine(srcDir, "agent", "modelqueue", "ModelQueueAdapter.cs");
        Assert.True(File.Exists(adapter), $"适配器源不在场: {adapter}");
        var lines = File.ReadAllLines(adapter);
        var idx = Array.FindIndex(lines, l => l.Contains("ActionLoopDiscipline.IsEnabled()"));
        Assert.True(idx >= 0, "注入点缺失 ⇒ 纪律不生效 (挂载类缺陷: 有代码行 ≠ 生效)");
        var br = Array.FindIndex(lines, l => l.Contains("_actionPort is not null && ActionLoopRunner.IsEnabled()"));
        Assert.True(br >= 0 && br < idx, "注入点必须在动作环分支头之后");
        Assert.True(idx - br <= 24, $"注入点距分支头 {idx - br} 行 ⇒ 疑似落在分支外");
        Assert.DoesNotContain("}", lines.Skip(br + 1).Take(idx - br - 1).Select(l => l.Trim()));
        Assert.Contains("ActionLoopDiscipline.Apply(qp.SystemPrompt)", lines[idx + 1]);

        // 反向锁: 全仓产品源恰 1 处调用 (既不漏接也不多处接)
        var calls = ProductSources(srcDir).Sum(f => File.ReadAllLines(f).Count(l => l.Contains("ActionLoopDiscipline.Apply(")));
        Assert.Equal(1, calls);
    }
}
