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

    // ---- R615 单变量轴 `AGENTFRAMEWORK_R1_ACTION_PROMPT`（**纯函数**判定，不写进程 env ⇒ 无并行污染）------
    // 轴关 = 旧行为**逐位等价**：旧块前缀的 sha 必须逐字等于 R610–R614 的冻结 pin（baselines 里那一行）。
    private const string R614FrozenPrefixSha =
        "a9792fdbe5b22f394a3149ca1bf3c1ba70927c1e537adabf36bbaed23f9dbc4e";

    [Fact]
    public void R615_轴关档_旧块逐位等于R614冻结pin()
    {
        var legacy = agent.contract.StructuredPrompt.PrefixFor(true);
        Assert.Equal(15675, legacy.Length);
        Assert.Equal(agent.contract.StructuredPrompt.PrefixLegacyChars, legacy.Length);
        Assert.Equal(R614FrozenPrefixSha, agent.contract.StructuredPrompt.Sha256Of(legacy));
        Assert.Equal(R614FrozenPrefixSha, agent.contract.StructuredPrompt.PrefixLegacySha256Pinned);
        Assert.Equal(agent.contract.StructuredPrompt.Sha256PinnedFor(true), agent.contract.StructuredPrompt.Sha256Of(legacy));
    }

    [Fact]
    public void R615_轴开档_新块钉子自洽且与旧块互异()
    {
        var neu = agent.contract.StructuredPrompt.PrefixFor(false);
        Assert.Equal(agent.contract.StructuredPrompt.PrefixChars, neu.Length);
        Assert.Equal(agent.contract.StructuredPrompt.PrefixSha256Pinned, agent.contract.StructuredPrompt.Sha256Of(neu));
        Assert.NotEqual(R614FrozenPrefixSha, agent.contract.StructuredPrompt.Sha256Of(neu));
        Assert.True(neu.Length >= agent.contract.StructuredPrompt.PrefixMinCharsForCache97);
        // 「只加厚」：两条前缀在**尾块起点之前逐位相同**（尾块整体置换，其后的 </prefix> 亦逐位同）。
        var legacy = agent.contract.StructuredPrompt.PrefixFor(true);
        var tailStart = legacy.IndexOf("<action_candidates>", StringComparison.Ordinal);
        Assert.True(tailStart > 0);
        Assert.Equal(legacy[..tailStart], neu[..tailStart]);
        // 负控：尾块之后（</prefix> 收尾）也逐位相同 —— 证明改动**只**落在尾块内部。
        var closeOld = legacy.IndexOf("\n\n</prefix>", tailStart, StringComparison.Ordinal);
        var closeNew = neu.IndexOf("\n\n</prefix>", tailStart, StringComparison.Ordinal);
        Assert.True(closeOld > 0 && closeNew > 0);
        Assert.Equal(legacy[closeOld..], neu[closeNew..]);
        // 且尾块确实变长（不是空改）
        Assert.True(closeNew - tailStart > closeOld - tailStart);
    }

    [Fact]
    public void R615_轴判定_仅legacy字样翻档_其余取值全落新块()
    {
        var f = agent.contract.StructuredPrompt.IsLegacyValue;
        Assert.True(f("legacy"));
        Assert.True(f(" legacy "));
        Assert.True(f("LEGACY"));
        // 负控：近似但不等于 ⇒ 缺省档（不得把拼写错误读成轴关臂）
        Assert.False(f("legacy2"));
        Assert.False(f("old"));
        Assert.False(f(""));
        Assert.False(f(null));
    }

    // ---- R617 单变量轴第二档 `r615`（对照臂 = R615 现盘块**逐位等价**） -------------------------------
    private const string R615FrozenPrefixSha =
        "8b8be6b8070e92a9d5d5bef697759c186c93b8ccafe47d55540b3393d95d351b";

    [Fact]
    public void R617_轴r615档_逐位等于R615冻结pin()
    {
        var r615 = agent.contract.StructuredPrompt.PrefixForCode(1);
        Assert.Equal(15794, r615.Length);
        Assert.Equal(agent.contract.StructuredPrompt.PrefixR615Chars, r615.Length);
        Assert.Equal(R615FrozenPrefixSha, agent.contract.StructuredPrompt.Sha256Of(r615));
        Assert.Equal(R615FrozenPrefixSha, agent.contract.StructuredPrompt.PrefixR615Sha256Pinned);
        Assert.Equal(agent.contract.StructuredPrompt.Sha256PinnedForCode(1), agent.contract.StructuredPrompt.Sha256Of(r615));
        Assert.Equal(agent.contract.StructuredPrompt.CharsForCode(1), r615.Length);
        // 三档互异（负控：任何两档不得同 sha）
        var cur = agent.contract.StructuredPrompt.PrefixForCode(0);
        var lg = agent.contract.StructuredPrompt.PrefixForCode(2);
        var shas = new[] { agent.contract.StructuredPrompt.Sha256Of(cur), agent.contract.StructuredPrompt.Sha256Of(r615), agent.contract.StructuredPrompt.Sha256Of(lg) };
        Assert.Equal(3, System.Linq.Enumerable.Distinct(shas).Count());
    }

    [Fact]
    public void R617_轴判定_仅r615字样翻档_近似拼写落缺省档()
    {
        var f = agent.contract.StructuredPrompt.IsR615Value;
        Assert.True(f("r615"));
        Assert.True(f(" r615 "));
        Assert.True(f("R615"));
        // 负控：近似但不等于 ⇒ 缺省档（不得把拼写错误读成对照臂）
        Assert.False(f("r6150"));
        Assert.False(f("r61"));
        Assert.False(f("legacy"));
        Assert.False(f(""));
        Assert.False(f(null));
        // 轴编码三档映射（纯函数）
        Assert.Equal(0, agent.contract.StructuredPrompt.AxisCode("r6150"));
        Assert.Equal(1, agent.contract.StructuredPrompt.AxisCode("R615"));
        Assert.Equal(2, agent.contract.StructuredPrompt.AxisCode("legacy"));
    }

    [Fact]
    public void R617_新档_只加厚_尾块置换且前后段逐位不变()
    {
        var r615 = agent.contract.StructuredPrompt.PrefixForCode(1);
        var neu = agent.contract.StructuredPrompt.PrefixForCode(0);
        var tailStart = r615.IndexOf("<action_candidates>", StringComparison.Ordinal);
        Assert.True(tailStart > 0);
        Assert.Equal(r615[..tailStart], neu[..tailStart]);
        var closeOld = r615.IndexOf("\n\n</prefix>", tailStart, StringComparison.Ordinal);
        var closeNew = neu.IndexOf("\n\n</prefix>", tailStart, StringComparison.Ordinal);
        Assert.True(closeOld > 0 && closeNew > 0);
        Assert.Equal(r615[closeOld..], neu[closeNew..]);
        Assert.NotEqual(r615[tailStart..closeOld], neu[tailStart..closeNew]);
        // 只加厚：新块严格不短于旧块，且整体前缀仍在 97% 缓存下限之上
        Assert.True(closeNew - tailStart >= closeOld - tailStart);
        Assert.True(neu.Length >= agent.contract.StructuredPrompt.PrefixMinCharsForCache97);
        // 负控：新块**必须仍含**「顶层必填」句（措辞轴真正的承重句），否则本轴改的不是被登记的自由度
        Assert.Contains("回复顶层必填字段", neu, StringComparison.Ordinal);
    }

    // ---- R630 单变量轴**第四档** `spec`（治理臂 = 缺省块 + 规格保真自检尾块；只加厚） ---------------------
    [Fact]
    public void R630_缺省档_逐位等于R617冻结pin_无治疗时行为不变()
    {
        var cur = agent.contract.StructuredPrompt.PrefixForCode(0);
        Assert.Equal(15796, cur.Length);
        Assert.Equal("25c97befa2124549b52991c0338324ceee7f7702a6348641ed917d3b7b658052",
            agent.contract.StructuredPrompt.Sha256Of(cur));
        Assert.Equal(agent.contract.StructuredPrompt.PrefixSha256Pinned, agent.contract.StructuredPrompt.Sha256Of(cur));
        // 轴关（未设 / 近似拼写）⇒ 一律缺省档 ⇒ 治疗段的清零是构造性的，不是运行期判断
        Assert.Equal(0, agent.contract.StructuredPrompt.AxisCode(null));
        Assert.Equal(0, agent.contract.StructuredPrompt.AxisCode(""));
        Assert.Equal(0, agent.contract.StructuredPrompt.AxisCode("spec0"));
    }

    [Fact]
    public void R630_轴判定_仅spec字样翻档_近似拼写落缺省档()
    {
        var f = agent.contract.StructuredPrompt.IsSpecValue;
        Assert.True(f("spec"));
        Assert.True(f(" SPEC "));
        Assert.True(f("Spec"));
        // 负控：近似但不等于 ⇒ 缺省档（不得把拼写错误读成治疗臂）
        Assert.False(f("specs"));
        Assert.False(f("spec_block"));
        Assert.False(f("r615"));
        Assert.False(f("legacy"));
        Assert.False(f(""));
        Assert.False(f(null));
        // 轴编码四档映射（纯函数，互斥）
        Assert.Equal(3, agent.contract.StructuredPrompt.AxisCode("spec"));
        Assert.Equal(0, agent.contract.StructuredPrompt.AxisCode("specs"));
        Assert.Equal(1, agent.contract.StructuredPrompt.AxisCode("r615"));
        Assert.Equal(2, agent.contract.StructuredPrompt.AxisCode("legacy"));
        Assert.Equal(0, agent.contract.StructuredPrompt.AxisCode(null));
    }

    [Fact]
    public void R630_治疗档_只加厚_插入点在闭合标签前且前段逐位不变()
    {
        var cur = agent.contract.StructuredPrompt.PrefixForCode(0);
        var spec = agent.contract.StructuredPrompt.PrefixForCode(3);
        var start = agent.contract.StructuredPrompt.PrefixSpecAppendStart;
        // 只加厚不变量：首次分歧下标之前的字节逐位相同（0..start-1 未动）
        Assert.True(start > 0);
        Assert.Equal(cur[..start], spec[..start]);
        Assert.NotEqual(cur[start], spec[start]);
        // 插入内容 = 规格保真尾块；闭合标签仍在末尾
        Assert.Contains("<spec_fidelity>", spec, StringComparison.Ordinal);
        Assert.EndsWith("</prefix>", spec, StringComparison.Ordinal);
        Assert.Equal(agent.contract.StructuredPrompt.PrefixSpecChars, spec.Length);
        Assert.Equal(16182, spec.Length);
        Assert.Equal(agent.contract.StructuredPrompt.PrefixSpecSha256Pinned, agent.contract.StructuredPrompt.Sha256Of(spec));
        Assert.Equal(agent.contract.StructuredPrompt.Sha256PinnedForCode(3), agent.contract.StructuredPrompt.Sha256Of(spec));
        // 严格加厚 + 仍在 97% 缓存下限之上；四档 sha 互异（负控：任何两档不得同 sha）
        Assert.True(spec.Length > cur.Length);
        Assert.True(spec.Length >= agent.contract.StructuredPrompt.PrefixMinCharsForCache97);
        var shas = new[]
        {
            agent.contract.StructuredPrompt.Sha256Of(cur),
            agent.contract.StructuredPrompt.Sha256Of(spec),
            agent.contract.StructuredPrompt.PrefixR615Sha256Pinned,
            agent.contract.StructuredPrompt.PrefixLegacySha256Pinned,
        };
        Assert.Equal(4, System.Linq.Enumerable.Distinct(shas).Count());
        // 承重句存在性（若尾块被删空，本轴改的不是被登记的自由度）
        Assert.Contains("判定覆盖全集", spec, StringComparison.Ordinal);
    }
}
