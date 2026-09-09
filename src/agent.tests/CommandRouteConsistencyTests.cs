using System;
using System.Linq;
using Xunit;
using agent.registry;

namespace agentframework.tests;

/// <summary>
/// v0.18.0 T1 (R339, 用户钦定防 LLM 幻觉假执行): 本地指令路由一致性审计 — Known 每指令必须 ∈
/// (TryRoute switch 臂 ∪ PreRoutedCommands 显式豁免)。防 /skills 首版事故 (Known 加了忘 switch 臂 →
/// 落 _=>NotCommand → 送 LLM 幻觉假执行) 与 /git 同类复发。switch 臂集合用 TryRoute 行为探测
/// (避免再维护一份字面表 — 行为即真相)。
/// </summary>
public class CommandRouteConsistencyTests
{
    [Fact]
    public void EveryKnownCommand_IsEitherSwitchArmed_OrExplicitlyPreRouted()
    {
        var missing = new System.Collections.Generic.List<string>();
        foreach (var cmd in LocalCommandRouter.KnownCommands)
        {
            var isPreRouted = LocalCommandRouter.PreRoutedCommands.Contains(cmd);
            // 行为探测: TryRoute 对 switch 臂指令返回 Handled=true; PreRouted 指令 TryRoute 返回
            // NotCommand (靠 V2 前置特判) — 两者皆合法; 其余 = 断裂 (会送 LLM 假执行)。
            var result = LocalCommandRouter.TryRoute(cmd);
            if (!isPreRouted && !result.Handled)
                missing.Add($"{cmd} (Known 含但无 switch 臂且非 PreRouted → TryRoute NotCommand → 将送 LLM 幻觉假执行)");
        }
        Assert.True(missing.Count == 0, "路由断裂指令: " + string.Join("; ", missing));
    }

    [Fact]
    public void EverySwitchArm_IsInKnown()
    {
        // 反向: switch 臂存在但不在 Known 的指令不可达 (Known 是唯一入口)
        // 行为探测无法枚举未知名 — 从 TryRoute 已知返回 Handled 的命令反查 Known 包含:
        foreach (var cmd in new[] { "/git", "/staged", "/activity", "/skills", "/stop", "/reset" })
            Assert.Contains(cmd, LocalCommandRouter.KnownCommands);
    }

    [Fact]
    public void PreRoutedCommands_AllInKnown()
    {
        foreach (var c in LocalCommandRouter.PreRoutedCommands)
            Assert.Contains(c, LocalCommandRouter.KnownCommands);
    }

    [Theory]
    [InlineData("/git", "git")]
    [InlineData("/staged", "staged")]
    [InlineData("/approve abc", "approve")]
    [InlineData("/activity", "activity")]
    [InlineData("/skills-only x,y", "skills-only")]
    [InlineData("/git status", "git")]
    public void ArmedCommands_HandledWithCommand(string input, string expectedCommand)
    {
        var r = LocalCommandRouter.TryRoute(input);
        Assert.True(r.Handled, $"{input} 应被本地拦截 (Handled) — 否则送 LLM 幻觉假执行");
        Assert.Equal(expectedCommand, r.Command);
    }

    [Theory]
    [InlineData("/model")]
    [InlineData("/balance")]
    public void PreRoutedCommands_TryRouteNotCommand_ByDesign(string input)
    {
        // V2 前置特判在 TryRoute 之前 — TryRoute 返回 NotCommand 是设计; 一致性由前置特判存在性保证
        var r = LocalCommandRouter.TryRoute(input);
        Assert.False(r.Handled);
    }

    [Fact]
    public void UnknownSlashCommand_NotHandled_AllowedToLLM()
    {
        // 未知 /x 送 LLM 属设计 (模型解释非本 CLI 指令); v0.18.0 T3 观察假执行模式
        var r = LocalCommandRouter.TryRoute("/totally-unknown-cmd-xyz");
        Assert.False(r.Handled);
    }
}
