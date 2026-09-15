using Xunit;
using agent.context;
using agent.registry;

namespace agent.tests;

/// <summary>
/// v0.23.0-exp12 · R391(C8) 机检: 形式化输出契约的**条件**前缀注入。
/// 判别力 (可证伪):
///   · 负控 —— 插件不在场时, 前缀必须**逐字不变** (一个字都不许多, 零 token 负担);
///   · 正向 —— 在场时契约段进入前缀, 且 token 增量有界 (不因注入而爆前缀);
///   · 槽隔离 —— 两种形态各自恒定, 不因调用顺序串味 (单槽缓存会在此处失败);
///   · 同源 —— 契约里的围栏标识/插件名与消费侧实现同值 (防"注入了却读不到"的断链)。
/// </summary>
public sealed class FormalPromptContractTests
{
    private static string Root() => Path.Combine(Path.GetTempPath(), "r391-prefix-probe");

    // ── 负控: 不在场 ⇒ 逐字不变 ───────────────────────────────────────────

    [Fact]
    public void Absent_Injection_Is_Byte_Identical()
    {
        var baseline = "基线正文: 不得改写一个字符";

        Assert.Equal(baseline, FormalPromptContract.Apply(baseline, formalPluginPresent: false));
        Assert.DoesNotContain(FormalPromptContract.FenceLanguage,
            FormalPromptContract.Apply(baseline, formalPluginPresent: false));
    }

    [Fact]
    public void SessionBaseline_Default_Overload_Equals_Explicit_Absent()
    {
        SessionBaseline.ResetForTests();

        var def = SessionBaseline.Build(Root());
        var absent = SessionBaseline.Build(Root(), formalPluginPresent: false);

        Assert.Equal(def, absent);
        Assert.DoesNotContain(FormalPromptContract.FenceLanguage, absent);
    }

    // ── 正向: 在场 ⇒ 契约进入前缀, 增量有界 ──────────────────────────────

    [Fact]
    public void Present_Injects_Contract_With_Bounded_Token_Delta()
    {
        SessionBaseline.ResetForTests();

        var absent = SessionBaseline.Build(Root(), formalPluginPresent: false);
        var present = SessionBaseline.Build(Root(), formalPluginPresent: true);

        Assert.Contains(FormalPromptContract.FenceLanguage, present);
        Assert.Contains("no_formal", present);

        var delta = FormalPromptContract.EstimateTokens(present) - FormalPromptContract.EstimateTokens(absent);
        Assert.InRange(delta, 1, 400);            // 增量必须是"小常量", 否则前缀注入得不偿失
        Assert.True(present.Length > absent.Length);
    }

    // ── 槽隔离: 交叉调用各自恒定 (单槽缓存必失败) ─────────────────────────

    [Fact]
    public void Two_Slots_Do_Not_Bleed_Across_Call_Order()
    {
        SessionBaseline.ResetForTests();

        var present = SessionBaseline.Build(Root(), formalPluginPresent: true);
        var absent = SessionBaseline.Build(Root(), formalPluginPresent: false);

        // 先在场后不在场: 若共用单槽缓存, absent 会拿到带契约的串 ⇒ 此处失败
        Assert.DoesNotContain(FormalPromptContract.FenceLanguage, absent);
        Assert.Contains(FormalPromptContract.FenceLanguage, present);

        // 再交叉一轮, 两种形态都必须与首次逐字相同 (前缀恒定 = 缓存有效)
        Assert.Equal(present, SessionBaseline.Build(Root(), formalPluginPresent: true));
        Assert.Equal(absent, SessionBaseline.Build(Root(), formalPluginPresent: false));

        // 重算后仍逐字相同 (与工作区快照无关的部分必须完全确定)
        SessionBaseline.ResetForTests();
        Assert.Equal(present, SessionBaseline.Build(Root(), formalPluginPresent: true));
        Assert.Equal(absent, SessionBaseline.Build(Root(), formalPluginPresent: false));
    }

    // ── 契约恒定 + 无路径泄漏 ────────────────────────────────────────────

    [Fact]
    public void Contract_Text_Is_Constant_And_Leak_Free()
    {
        Assert.Equal(FormalPromptContract.Build(), FormalPromptContract.Build());
        Assert.DoesNotContain(Root(), FormalPromptContract.Build());
        Assert.NotEmpty(FormalPromptContract.Build());
    }

    // ── 同源机检: 注入侧与消费侧标识必须一致 ─────────────────────────────

    [Fact]
    public void Contract_Ids_Match_Consumer_Side()
    {
        Assert.Equal(ClickProofFence.Language, FormalPromptContract.FenceLanguage);
        Assert.Equal(ClickRoverSegmentPlugin.PluginId, FormalPromptContract.PluginName);
    }

    [Fact]
    public void IsPresent_Is_Whole_Word_Match()
    {
        Assert.True(FormalPromptContract.IsPresent(["ui.capture", ClickRoverSegmentPlugin.PluginId]));
        Assert.False(FormalPromptContract.IsPresent([]));
        Assert.False(FormalPromptContract.IsPresent(null));
        // 负控: 不做前缀/包含匹配
        Assert.False(FormalPromptContract.IsPresent([ClickRoverSegmentPlugin.PluginId + ".extra"]));
        Assert.False(FormalPromptContract.IsPresent(["x" + ClickRoverSegmentPlugin.PluginId]));
    }

    // ── R461: 契约声明不上前台 (契约是给本地验证器看的, 用户不该读到) ──────

    [Fact]
    public void SplitFacing_Removes_Fenced_Block()
    {
        var text = "已写入 first.txt (3 行)。\n\n```" + FormalPromptContract.FenceLanguage +
                   "\npremise 1 > 0\ngoal 3 == 3\n```";
        var (visible, declaration) = FormalPromptContract.SplitFacing(text);

        Assert.Contains("已写入", visible);
        Assert.DoesNotContain("premise", visible);
        Assert.DoesNotContain("```", visible);
        Assert.Contains("premise 1 > 0", declaration);
    }

    [Fact]
    public void SplitFacing_Removes_Bare_Block_Then_Resumes_Normal_Text()
    {
        // 实发形态 (R460 run T4): 模型不写围栏, 直接裸写 5 行
        var bare = "已写入 stats.txt。\n" + FormalPromptContract.FenceLanguage +
                   "\npremise 1 > 0\ngoal 2 > 1\n后面还有正常文字。";
        var (visible, declaration) = FormalPromptContract.SplitFacing(bare);

        Assert.DoesNotContain("premise", visible);
        Assert.Contains("已写入 stats.txt。", visible);
        Assert.Contains("后面还有正常文字。", visible);   // 裸块结束即恢复正文
        Assert.Contains("goal 2 > 1", declaration);

        var (v2, d2) = FormalPromptContract.SplitFacing("结果是这样。\nno_formal: 本步无法用整数断言表达");
        Assert.Equal("结果是这样。", v2.Trim());
        Assert.Contains("no_formal:", d2);
    }

    [Fact]
    public void SplitFacing_FailSafe_Never_Blanks_The_Reply()
    {
        var onlyDeclaration = "```" + FormalPromptContract.FenceLanguage + "\nno_formal: 无\n```";
        var (visible, declaration) = FormalPromptContract.SplitFacing(onlyDeclaration);

        Assert.False(string.IsNullOrWhiteSpace(visible));   // 宁可少剥, 也不给用户空回复
        Assert.NotEmpty(declaration);
    }

    [Fact]
    public void SplitFacing_Leaves_Non_Contract_Content_Byte_Identical()
    {
        // 正控: 不含契约时一个字都不动
        Assert.Equal("正常回复。", FormalPromptContract.SplitFacing("正常回复。").Visible);
        // 其它语言围栏 = 正常内容 (不能被误剥)
        var (visible, declaration) = FormalPromptContract.SplitFacing("看代码:\n```csharp\nvar x = 1;\n```\n完。");
        Assert.Contains("var x = 1;", visible);
        Assert.Empty(declaration);
    }
}
