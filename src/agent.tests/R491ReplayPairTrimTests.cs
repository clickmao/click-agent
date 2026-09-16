using System;
using System.Collections.Generic;
using agent.core;
using agent.intent;
using agent.modelqueue;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// R491 候选③: 回放**配对剪裁** (闸 <see cref="ReplayPairTrim.EnvName"/>, 默认关) 的判据表 + 字节级断言。
///
/// 命题: 零远端调用轮的 **assistant 侧**已在 R490 剔出远端回放; 该轮的 **user 侧**同样从未随任何
/// 请求发出过 ⇒ 留在回放里只造成 user→user 相邻 (上游把两段用户文本当同轮输入) + 白付 token。
/// 判据来源: R489 实测请求体逐字回放本地产物; R490 只补了 assistant 侧 (缺口)。
/// </summary>
public sealed class R491ReplayPairTrimTests
{
    private static Prompt PromptWith(params (MessageRole Role, string Content)[] history)
    {
        var p = new Prompt { SystemPrompt = "sys", UserMessage = "当前轮", Intent = IntentRecognizer.Intents.General };
        foreach (var (role, content) in history)
            p.History.Add(new PromptMessage { Role = role, Content = content });
        return p;
    }

    private static List<string> Contents(QueuePrompt qp) => qp.History.ConvertAll(h => h.Content);

    // ── 闸取值判据 ───────────────────────────────────────────────────────────

    [Theory]
    [InlineData(null, false)]
    [InlineData("", false)]
    [InlineData("   ", false)]
    [InlineData("0", false)]
    [InlineData("off", false)]
    [InlineData("false", false)]
    [InlineData("no", false)]
    [InlineData("1", true)]
    [InlineData(" true ", true)]
    [InlineData("TRUE", true)]
    [InlineData("True", true)]
    public void GateValue_IsJudgedBySingleSource(string? value, bool expected)
        => Assert.Equal(expected, ReplayPairTrim.Decide(value));

    [Fact]
    public void GateEnv_UnsetMeansOff_ZeroRegression()
    {
        var saved = Environment.GetEnvironmentVariable(ReplayPairTrim.EnvName);
        try
        {
            Environment.SetEnvironmentVariable(ReplayPairTrim.EnvName, null);
            Assert.False(ReplayPairTrim.IsEnabled());          // 未设 = 关 ⇒ 回放面与 R490 逐字节相同
            Assert.Equal("0", ReplayPairTrim.Stamp());
            Environment.SetEnvironmentVariable(ReplayPairTrim.EnvName, "1");
            Assert.True(ReplayPairTrim.IsEnabled());
            Assert.Equal("1", ReplayPairTrim.Stamp());
        }
        finally
        {
            Environment.SetEnvironmentVariable(ReplayPairTrim.EnvName, saved);
        }
    }

    // ── 两态判据表 (显式传态, 不改环境变量) ──────────────────────────────────

    private static Prompt SkipTurnHistory() => PromptWith(
        (MessageRole.User, "把构建命令写成一行。"),
        (MessageRole.Assistant, "先把工作区看清: 没有 src/。"),
        (MessageRole.User, "收到，谢谢。"),                              // ← 零远端调用轮的 user 侧
        (MessageRole.Assistant, ModelQueueRouter.LocalSkipFallback),     // ← R490 已剔 (assistant 侧)
        (MessageRole.User, "继续。"));

    [Fact]
    public void PairTrimOff_KeepsUserSideOfSkipTurn()
    {
        var qp = ModelQueueAdapter.ToQueuePrompt(SkipTurnHistory(), pairTrim: false);
        Assert.Equal(1, qp.ReplayTrimmedLocalTemplates);
        Assert.Equal(0, qp.ReplayTrimmedLocalUserTurns);
        Assert.Equal(new[] { "把构建命令写成一行。", "先把工作区看清: 没有 src/。", "收到，谢谢。", "继续。" },
            Contents(qp));
        // 旧态 (闸关) 的 user→user 相邻缺陷仍在 —— 这正是 R491 要修的面, 断言它仍可复现 (零回归证据)
        Assert.Equal(new[] { "user", "assistant", "user", "user" },
            qp.History.ConvertAll(h => h.Role));
    }

    [Fact]
    public void PairTrimOn_DropsWholeZeroRemoteCallTurn()
    {
        var qp = ModelQueueAdapter.ToQueuePrompt(SkipTurnHistory(), pairTrim: true);
        Assert.Equal(1, qp.ReplayTrimmedLocalTemplates);
        Assert.Equal(1, qp.ReplayTrimmedLocalUserTurns);
        Assert.Equal(new[] { "把构建命令写成一行。", "先把工作区看清: 没有 src/。", "继续。" }, Contents(qp));
        // 不变量: 配对剪裁后不得出现 user→user 相邻 (回放面形状合法化)
        for (var i = 1; i < qp.History.Count; i++)
            Assert.False(qp.History[i - 1].Role == "user" && qp.History[i].Role == "user",
                $"pair_trim_on 后仍出现 user→user 相邻 @{i}");
    }

    [Fact]
    public void PairTrimOn_TemplateAtHead_HasNoUserToDrop()
    {
        var p = PromptWith(
            (MessageRole.Assistant, ModelQueueRouter.LocalSkipFallback),
            (MessageRole.User, "继续。"));
        var qp = ModelQueueAdapter.ToQueuePrompt(p, pairTrim: true);
        Assert.Equal(1, qp.ReplayTrimmedLocalTemplates);
        Assert.Equal(0, qp.ReplayTrimmedLocalUserTurns);      // 无紧邻前置 user ⇒ 只剔 assistant 侧
        Assert.Equal(new[] { "继续。" }, Contents(qp));
    }

    [Fact]
    public void PairTrimOn_ConsecutiveSkipTurns_EachPairsAtMostOnce()
    {
        var p = PromptWith(
            (MessageRole.User, "收到。"),
            (MessageRole.Assistant, ModelQueueRouter.LocalSkipFallback),
            (MessageRole.User, "好的。"),
            (MessageRole.Assistant, ModelQueueRouter.LocalSkipFallback));
        var qp = ModelQueueAdapter.ToQueuePrompt(p, pairTrim: true);
        Assert.Equal(2, qp.ReplayTrimmedLocalTemplates);
        Assert.Equal(2, qp.ReplayTrimmedLocalUserTurns);
        Assert.Empty(qp.History);                             // 两轮都是零远端调用 ⇒ 全剔
    }

    [Fact]
    public void PairTrimOn_DoesNotTouchSubstantiveReplies()
    {
        // R465/R475 复述轮: 本地答复 = 上一条**实质**答复原文 (provider 产出) ⇒ 连带其 user 侧必须保留
        var substantive = "当前进度: count.txt=4, merged.txt=ALPHA/BETA/GAMMA。";
        var p = PromptWith(
            (MessageRole.User, "继续。"),
            (MessageRole.Assistant, substantive));
        var qp = ModelQueueAdapter.ToQueuePrompt(p, pairTrim: true);
        Assert.Equal(0, qp.ReplayTrimmedLocalTemplates);
        Assert.Equal(0, qp.ReplayTrimmedLocalUserTurns);
        Assert.Equal(new[] { "继续。", substantive }, Contents(qp));
    }

    // ── 字节级: 装配后的 messages 数组 ───────────────────────────────────────

    [Fact]
    public void PairTrimOn_SkipTurnTextAbsentFromAssembledMessages()
    {
        const string ack = "收到，谢谢。";
        var on = ModelQueueRouter.BuildMessages(ModelQueueAdapter.ToQueuePrompt(SkipTurnHistory(), pairTrim: true));
        var off = ModelQueueRouter.BuildMessages(ModelQueueAdapter.ToQueuePrompt(SkipTurnHistory(), pairTrim: false));

        var onTexts = on.ConvertAll(m => m.Content);
        var offTexts = off.ConvertAll(m => m.Content);

        Assert.Contains(ack, offTexts);                        // 旧态: 白付 token 的字节证据
        Assert.DoesNotContain(ack, onTexts);                   // 新态: 该轮整体不发往远端
        Assert.Equal(offTexts.Count - 1, onTexts.Count);       // 恰好少一条 (user 侧)

        // 前缀不变量: 剪裁点之前的字节面完全不变 ⇒ provider 前缀缓存不受影响
        Assert.Equal(offTexts[0], onTexts[0]);
        Assert.Equal(offTexts[1], onTexts[1]);
    }

    // ── 动作环 Clone 透传 (打点与实发面同寿命) ───────────────────────────────

    [Fact]
    public void ActionLoopClone_PropagatesPairTrimCounters()
    {
        var qp = new QueuePrompt
        {
            SystemPrompt = "s",
            UserMessage = "u",
            Intent = IntentRecognizer.Intents.General,
            ReplayTrimmedLocalTemplates = 3,
            ReplayTrimmedLocalUserTurns = 2,
        };
        var clone = ActionLoopRunner.Clone(qp, new List<QueuePostUserMessage>());
        Assert.Equal(3, clone.ReplayTrimmedLocalTemplates);
        Assert.Equal(2, clone.ReplayTrimmedLocalUserTurns);
        Assert.Equal(qp.History.Count, clone.History.Count);
    }
}
