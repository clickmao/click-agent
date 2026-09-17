using agent.context;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R524 前缀稳定性机检 —— 依据 (用户 2026-09-17 定向 + 真机逐字节比对):
///   system 提示里混入了**按运行变化**的内容 (`data/activity/&lt;pid&gt;.json`, pid 逐轮不同且 TaskSummary 就是题面原文),
///   ⇒ R522 窗口 + R523 三窗口四份实发 system 只在第 4,477 字符处分叉, 首调用缓存命中 2,304 tok 与该 frontier 吻合
///   (4,477 × 0.515 ≈ 2,306) ⇒ 跨轮可缓存前缀被砍在 4,477, 其后 757 字符每轮重算。
/// 三条锁:
///   ① 工作区文件块不再算会话静态 ⇒ 只进本轮 user 尾部追加区, system 提示逐字节常量;
///   ② 自指遥测路径 (activity/telemetry/*.jsonl) 不得被自动召回 (显式工具读取仍可用);
///   ③ 工具回执缺省压到摘要量级 (缺省 600 字符, 硬顶 8192, env 可调)。
/// 形状标杆 (同题 codex 五调用): 每步回执 105–253 字符, 5 轮上下文只涨 1,757 tok。
/// </summary>
public sealed class R524PrefixStabilityTests
{
    private const string EnvChars = "AGENTFRAMEWORK_ACTION_RESULT_CHARS";

    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !Directory.Exists(Path.Combine(dir.FullName, "src"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return dir!.FullName;
    }

    private static string Source(string relative) => SourcePin.Text(relative.Replace(Path.DirectorySeparatorChar, '/'));

    [Fact]
    public void 工作区文件块不再视为会话静态()
    {
        Assert.False(SessionInjectionPlanner.IsSessionStatic("Workspace Files"));
        Assert.False(SessionInjectionPlanner.IsSessionStatic("工作区文件 data/activity/2803414.json"));
        // 真正的会话常量仍必须留在静态面 (回归护栏: 别把白名单捶空)
        Assert.True(SessionInjectionPlanner.IsSessionStatic("User Preference"));
        Assert.True(SessionInjectionPlanner.IsSessionStatic("可用能力"));
        Assert.True(SessionInjectionPlanner.IsSessionStatic("AgentContext"));
    }

    [Fact]
    public void 结构锁_静态白名单不含工作区文件()
    {
        var text = Source(Path.Combine("src", "agent", "context", "SessionInjectionPlanner.cs"));
        var i = text.IndexOf("StaticTitlePrefixes", StringComparison.Ordinal);
        Assert.True(i > 0, "找不到静态白名单数组");
        var arr = text.Substring(i, Math.Min(400, text.Length - i));
        Assert.DoesNotContain("工作区文件", arr, StringComparison.Ordinal);
        Assert.DoesNotContain("Workspace Files", arr, StringComparison.Ordinal);
        Assert.Contains("User Preference", arr, StringComparison.Ordinal);
    }

    [Fact]
    public void 遥测路径闸_结构性排除_且不误伤源码()
    {
        Assert.True(ContextAssembler.IsSelfTelemetryPath("/w/data/activity/2803414.json"));
        Assert.True(ContextAssembler.IsSelfTelemetryPath("/w/data/prompt_audit.jsonl"));
        Assert.True(ContextAssembler.IsSelfTelemetryPath(@"C:\w\data\telemetry\host.json"));
        Assert.True(ContextAssembler.IsSelfTelemetryPath("/w/.state/state.db"));
        Assert.False(ContextAssembler.IsSelfTelemetryPath("/w/src/games/life.py"));
        Assert.False(ContextAssembler.IsSelfTelemetryPath("/w/docs/plans/r524.md"));
        Assert.False(ContextAssembler.IsSelfTelemetryPath(""));
    }

    [Fact]
    public void 结构锁_工作区召回接入遥测闸()
    {
        var text = Source(Path.Combine("src", "agent", "contextassembler", "ContextAssembler.cs"));
        Assert.Contains("!IsSelfTelemetryPath(f)", text, StringComparison.Ordinal);
    }

    [Fact]
    public void 回执缺省上限_摘要量级且可调_上不超硬顶()
    {
        var saved = Environment.GetEnvironmentVariable(EnvChars);
        try
        {
            Environment.SetEnvironmentVariable(EnvChars, null);
            Assert.Equal(600, ActionLoopRunner.ToolResultCharCap());
            Environment.SetEnvironmentVariable(EnvChars, "3000");
            Assert.Equal(3000, ActionLoopRunner.ToolResultCharCap());
            Environment.SetEnvironmentVariable(EnvChars, "99999");
            Assert.Equal(ActionLoopRunner.MaxToolResultBytes, ActionLoopRunner.ToolResultCharCap());
            Environment.SetEnvironmentVariable(EnvChars, "abc");
            Assert.Equal(ActionLoopRunner.DefaultToolResultChars, ActionLoopRunner.ToolResultCharCap());
        }
        finally
        {
            Environment.SetEnvironmentVariable(EnvChars, saved);
        }
    }

    [Fact]
    public void 结构锁_回灌走可调上限而非硬顶()
    {
        var text = Source(Path.Combine("src", "agent.modelqueue", "ActionLoopRunner.cs"));
        Assert.Contains("res.Render(ToolResultCharCap())", text, StringComparison.Ordinal);
        Assert.DoesNotContain("res.Render(MaxToolResultBytes)", text, StringComparison.Ordinal);
    }

    [Fact]
    public void 纪律含零过渡叙述与按需回执()
    {
        Assert.Contains("零过渡叙述", ActionLoopDiscipline.Text, StringComparison.Ordinal);
        Assert.Contains("回执按需取全文", ActionLoopDiscipline.Text, StringComparison.Ordinal);
    }

    [Fact]
    public void 工作区召回缺省关_显式才开()
    {
        var saved = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_WORKSPACE_RECALL");
        try
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_WORKSPACE_RECALL", null);
            Assert.False(agent.context.ContextAssembler.IsWorkspaceRecallEnabled());
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_WORKSPACE_RECALL", "off");
            Assert.False(agent.context.ContextAssembler.IsWorkspaceRecallEnabled());
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_WORKSPACE_RECALL", "on");
            Assert.True(agent.context.ContextAssembler.IsWorkspaceRecallEnabled());
        }
        finally
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_WORKSPACE_RECALL", saved);
        }
    }

    [Fact]
    public void 结构锁_召回受开关约束()
    {
        var text = Source(Path.Combine("src", "agent", "contextassembler", "ContextAssembler.cs"));
        Assert.Contains("IsWorkspaceRecallEnabled() &&", text, StringComparison.Ordinal);
        Assert.Contains("!IsSelfTelemetryPath(f)", text, StringComparison.Ordinal);
    }

    [Fact]
    public void 技能知识参考属常量前缀_RAG与守卫仍动态()
    {
        Assert.True(agent.context.SessionInjectionPlanner.IsSessionStatic("技能知识参考"));
        Assert.False(agent.context.SessionInjectionPlanner.IsSessionStatic("Memory (RAG)"));
        Assert.False(agent.context.SessionInjectionPlanner.IsSessionStatic("GuardrailMemory"));
        Assert.False(agent.context.SessionInjectionPlanner.IsSessionStatic("本轮参考上下文"));
    }

    [Fact]
    public void 结构锁_技能知识参考焊进常量前缀而非user轮()
    {
        var text = Source(Path.Combine("src", "agent", "IndustrialAgentV2.cs"));
        Assert.Contains("var skillConst = _pendingSkillKnowledge.Length > 0", text, StringComparison.Ordinal);
        Assert.Contains("+ skillConst;", text, StringComparison.Ordinal);
        Assert.Contains("if (skillConst.Length > 0) _pendingSkillKnowledge = string.Empty;", text, StringComparison.Ordinal);
    }
}
