using System;
using System.Collections.Generic;
using System.Text.Json;
using agent.core;
using agent.intent;
using agent.modelqueue;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// R490: 声明面按需 (ToolDeclGate) + 回放剪裁 (本地模板答复不入远端前缀) 的判据表与请求字节级断言。
/// 依据: `eval/rover/r489/calls-*.jsonl` —— 51 次远端请求全部 tools_n=4 且 12 轮 intent 全为 general;
/// 100 条 assistant「收到。」被逐字回放。
/// </summary>
public sealed class R490ToolDeclGateTests
{
    private static Prompt PromptWith(params (MessageRole Role, string Content)[] history)
    {
        var p = new Prompt { SystemPrompt = "sys", UserMessage = "当前轮", Intent = IntentRecognizer.Intents.General };
        foreach (var (role, content) in history)
            p.History.Add(new PromptMessage { Role = role, Content = content });
        return p;
    }

    // ── 声明面判据 ───────────────────────────────────────────────────────────

    [Fact]
    public void GateOff_DeclaresForEveryIntent()
    {
        foreach (var intent in IntentRecognizer.KnownIntents)
            Assert.True(ToolDeclGate.ShouldDeclare(intent, gateEnabled: false), intent);
        Assert.True(ToolDeclGate.ShouldDeclare(null, gateEnabled: false));
        Assert.Equal("gate_off", ToolDeclGate.DecideReason(IntentRecognizer.Intents.General, gateEnabled: false));
    }

    [Fact]
    public void GateOn_DropsDeclarationForNonToolIntents()
    {
        foreach (var intent in new[]
                 {
                     IntentRecognizer.Intents.General,
                     IntentRecognizer.Intents.Search,
                     IntentRecognizer.Intents.MemorySearch,
                 })
        {
            Assert.False(ToolDeclGate.ShouldDeclare(intent, gateEnabled: true), intent);
            Assert.Equal("non_tool_intent_drop", ToolDeclGate.DecideReason(intent, gateEnabled: true));
        }
    }

    [Fact]
    public void GateOn_KeepsDeclarationForToolIntents()
    {
        Assert.Equal(6, ToolDeclGate.ToolIntents.Length);
        foreach (var intent in ToolDeclGate.ToolIntents)
        {
            Assert.True(ToolDeclGate.ShouldDeclare(intent, gateEnabled: true), intent);
            Assert.Equal("tool_intent_keep", ToolDeclGate.DecideReason(intent, gateEnabled: true));
        }
    }

    /// <summary>
    /// 同源锁 (机检): 库里以字面量持有意图键 ⇒ 必须逐值等于分类器常量, 且分类器改名/新增即红。
    /// 期望值来自 IntentRecognizer 侧 (产品自身常量), 非本测试手抄。
    /// </summary>
    [Fact]
    public void ToolIntents_AreLockedToIntentRecognizerConstants()
    {
        var expected = new[]
        {
            IntentRecognizer.Intents.CodeGeneration,
            IntentRecognizer.Intents.CodeModification,
            IntentRecognizer.Intents.CodeReview,
            IntentRecognizer.Intents.TestGeneration,
            IntentRecognizer.Intents.FileOperation,
            IntentRecognizer.Intents.GitOperation,
        };
        Assert.Equal(expected, ToolDeclGate.ToolIntents);
        foreach (var t in ToolDeclGate.ToolIntents)
            Assert.Contains(t, IntentRecognizer.KnownIntents);
        // 对话/检索类**不得**进工作区动作集 (门开后必须丢声明的那批)
        foreach (var t in new[] { IntentRecognizer.Intents.General, IntentRecognizer.Intents.Search, IntentRecognizer.Intents.MemorySearch })
            Assert.DoesNotContain(t, ToolDeclGate.ToolIntents);
        // KnownIntents 无未归类项: 分类器新增意图必须在本轮被显式归类 (丢声明 or 保声明)
        Assert.Equal(IntentRecognizer.KnownIntents.Count, expected.Length + 3);
    }

    [Fact]
    public void UnknownIntent_IsKeptConservative()
    {
        // 未命中判据不得变成能力丢失: 空/未知意图 ⇒ 仍然声明
        Assert.True(ToolDeclGate.ShouldDeclare(null, gateEnabled: true));
        Assert.True(ToolDeclGate.ShouldDeclare("", gateEnabled: true));
        Assert.True(ToolDeclGate.ShouldDeclare("   ", gateEnabled: true));
        Assert.Equal("unknown_intent_keep", ToolDeclGate.DecideReason(null, gateEnabled: true));
        // 已知但不在工作区动作集: 丢弃 (大小写不敏感)
        Assert.False(ToolDeclGate.ShouldDeclare("GENERAL", gateEnabled: true));
    }

    [Fact]
    public void ToolDeclGate_EnvSwitch_DefaultOff()
    {
        var saved = Environment.GetEnvironmentVariable(ToolDeclGate.EnvName);
        try
        {
            Environment.SetEnvironmentVariable(ToolDeclGate.EnvName, null);
            Assert.False(ToolDeclGate.IsEnabled());                       // 未设 = 关 (生产行为不变)
            Environment.SetEnvironmentVariable(ToolDeclGate.EnvName, "off");
            Assert.False(ToolDeclGate.IsEnabled());
            Environment.SetEnvironmentVariable(ToolDeclGate.EnvName, "0");
            Assert.False(ToolDeclGate.IsEnabled());
            Environment.SetEnvironmentVariable(ToolDeclGate.EnvName, "false");
            Assert.False(ToolDeclGate.IsEnabled());
            Environment.SetEnvironmentVariable(ToolDeclGate.EnvName, "on");
            Assert.True(ToolDeclGate.IsEnabled());
            Environment.SetEnvironmentVariable(ToolDeclGate.EnvName, "1");
            Assert.True(ToolDeclGate.IsEnabled());
        }
        finally
        {
            Environment.SetEnvironmentVariable(ToolDeclGate.EnvName, saved);
        }
    }

    // ── 请求字节面 (声明有 = tools 键在; 声明无 = tools 键不在) ────────────────

    private static string Body(Prompt p, string? toolsJson)
    {
        var qp = ModelQueueAdapter.ToQueuePrompt(p);
        qp.ToolsJson = toolsJson;
        var msgs = ModelQueueRouter.BuildMessages(qp);
        return ModelQueueRouter.SerializeChatRequest(new QueueChatRequest
        {
            Model = "deepseek-flash",
            Messages = msgs,
            ToolsJson = toolsJson,
        });
    }

    [Fact]
    public void DeclaredRequest_CarriesToolsJsonVerbatim()
    {
        var body = Body(PromptWith((MessageRole.User, "hi")), ActionToolSpec.ChatToolsJson);
        Assert.Contains("\"tools\":" + ActionToolSpec.ChatToolsJson, body, StringComparison.Ordinal);
    }

    [Fact]
    public void SuppressedRequest_CarriesNoToolsKey()
    {
        var body = Body(PromptWith((MessageRole.User, "hi")), null);
        Assert.DoesNotContain("\"tools\"", body, StringComparison.Ordinal);
        // 与门关时的单轮请求逐字节相同 (零回归面)
        Assert.Equal(body, Body(PromptWith((MessageRole.User, "hi")), null));
    }

    // ── 回放剪裁 ─────────────────────────────────────────────────────────────

    [Fact]
    public void LocalTemplateReply_IsTrimmedFromRemoteReplay()
    {
        Assert.True(ModelQueueAdapter.IsLocalTemplateReply(ModelQueueRouter.LocalSkipFallback));
        Assert.True(ModelQueueAdapter.IsLocalTemplateReply("  " + ModelQueueRouter.LocalSkipFallback + " "));
        Assert.False(ModelQueueAdapter.IsLocalTemplateReply(null));
        Assert.False(ModelQueueAdapter.IsLocalTemplateReply("收到。已按你说的改完。"));   // 实质答复 ≠ 模板
        Assert.False(ModelQueueAdapter.IsLocalTemplateReply("")); 

        var p = PromptWith(
            (MessageRole.User, "把构建命令写成一行。"),
            (MessageRole.Assistant, "先把工作区看清: 没有 src/。"),
            (MessageRole.User, "收到，谢谢。"),
            (MessageRole.Assistant, ModelQueueRouter.LocalSkipFallback),   // 本地模板 (零远端调用产物)
            (MessageRole.User, "继续。"));

        var qp = ModelQueueAdapter.ToQueuePrompt(p);

        Assert.Equal(1, qp.ReplayTrimmedLocalTemplates);
        Assert.Equal(4, qp.History.Count);
        Assert.Equal(new[] { "把构建命令写成一行。", "先把工作区看清: 没有 src/。", "收到，谢谢。", "继续。" },
            qp.History.ConvertAll(h => h.Content));
        Assert.Equal(new[] { "user", "assistant", "user", "user" }, qp.History.ConvertAll(h => h.Role));

        // 装配后的 messages 数组里不得出现模板串 (机检不变量)
        var msgs = ModelQueueRouter.BuildMessages(qp);
        foreach (var m in msgs)
            Assert.NotEqual(ModelQueueRouter.LocalSkipFallback, m.Content);
    }

    [Fact]
    public void RepeatReplaySubstantiveReply_IsKept()
    {
        // R465/R475 复述轮: 本地答复 = 上一条**实质**答复原文 (provider 产出) ⇒ 必须保留回放
        var substantive = "当前进度: count.txt=4, merged.txt=ALPHA/BETA/GAMMA。";
        var p = PromptWith(
            (MessageRole.User, "继续。"),
            (MessageRole.Assistant, substantive));
        var qp = ModelQueueAdapter.ToQueuePrompt(p);
        Assert.Equal(0, qp.ReplayTrimmedLocalTemplates);
        Assert.Equal(2, qp.History.Count);
        Assert.Equal(substantive, qp.History[1].Content);
    }

    // ── 动作环 Clone 透传 (打点完整性) ────────────────────────────────────────

    [Fact]
    public void ActionLoopClone_PropagatesGateFacts()
    {
        // R490 实测踩中: 每次远端调用都经 ActionLoopRunner.Clone ⇒ 若 Clone 不透传这三项,
        // (a) 声明面判据在环内调用上丢失, (b) 「剪裁了 N 条」打点恒 0 ⇒ 打点与实发面脱钩
        //     (T1 首跑: 请求体内模板串确已消失, 但 tool_decl_gate.replay_trimmed 全 0)。
        var qp = new QueuePrompt
        {
            SystemPrompt = "s",
            UserMessage = "u",
            Intent = IntentRecognizer.Intents.General,
            ToolsJson = ActionToolSpec.ChatToolsJson,
            ReplayTrimmedLocalTemplates = 2,
        };
        var clone = ActionLoopRunner.Clone(qp, new List<QueuePostUserMessage>());
        Assert.Equal(IntentRecognizer.Intents.General, clone.Intent);
        Assert.Equal(ActionToolSpec.ChatToolsJson, clone.ToolsJson);
        Assert.Equal(2, clone.ReplayTrimmedLocalTemplates);
        // 剪裁后的 History 不得在 Clone 里被还原
        Assert.Equal(qp.History.Count, clone.History.Count);
    }
}
