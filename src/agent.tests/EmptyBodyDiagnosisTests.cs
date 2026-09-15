using System;
using System.IO;
using agent.modelqueue;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R478 判据面 (承 R477 真机 20/20 空正文调用 `finish_reason=tool_calls`):
///   A. **空正文定因**: 判据只取上游协议字段 (finish_reason / tool_calls 计数), 禁关键词猜测;
///   B. **误诊禁止回落**: 旧文案「推理过程占满了输出预算」不得再出现 (它把 tool_calls 记成预算问题,
///      并因此白跑一次 32k 预算重试 = 调用数 + token 双浪费);
///   C. **因果 id**: llm_call.request_id ↔ loop_turn.request_id 同值可 join (替代时间窗归属)。
/// </summary>
public class EmptyBodyDiagnosisTests
{
    // ---------- A. 定因 (纯函数) ----------

    [Theory]
    [InlineData("tool_calls", 0, 0, EmptyBodyCause.ToolCall)]        // 上游自报协议字段
    [InlineData("stop", 2, 0, EmptyBodyCause.ToolCall)]              // 计数优先 (上游未报 reason 但确实给了 tool_calls)
    [InlineData("length", 0, 900, EmptyBodyCause.LengthExhausted)]
    [InlineData("", 0, 500, EmptyBodyCause.LengthExhausted)]         // 未报原因 ∧ 有推理 ⇒ 与 length 同一失效面
    [InlineData("", 0, 0, EmptyBodyCause.Unknown)]
    [InlineData("stop", 0, 0, EmptyBodyCause.UpstreamStop)]
    [InlineData("content_filter", 0, 0, EmptyBodyCause.Unknown)]
    [InlineData(null, 0, 0, EmptyBodyCause.Unknown)]
    public void A1_分类只取协议字段(string? reason, int toolCalls, int reasoningChars, EmptyBodyCause expect)
        => Assert.Equal(expect, EmptyBodyDiagnosis.Classify(reason, toolCalls, reasoningChars));

    [Fact]
    public void A2_工具调用不可重试_其余可重试()
    {
        Assert.False(EmptyBodyDiagnosis.Retryable(EmptyBodyCause.ToolCall));
        Assert.True(EmptyBodyDiagnosis.Retryable(EmptyBodyCause.LengthExhausted));
        Assert.True(EmptyBodyDiagnosis.Retryable(EmptyBodyCause.UpstreamStop));
        Assert.True(EmptyBodyDiagnosis.Retryable(EmptyBodyCause.Unknown));
    }

    [Fact]
    public void A3_只有工具执行面启用且确有tool_calls才交给动作环()
    {
        Assert.True(EmptyBodyDiagnosis.RoutableToActionLoop(EmptyBodyCause.ToolCall, 1, true));
        Assert.False(EmptyBodyDiagnosis.RoutableToActionLoop(EmptyBodyCause.ToolCall, 1, false));   // 面未启用
        Assert.False(EmptyBodyDiagnosis.RoutableToActionLoop(EmptyBodyCause.ToolCall, 0, true));    // 无 tool_calls ⇒ 无处可交
        Assert.False(EmptyBodyDiagnosis.RoutableToActionLoop(EmptyBodyCause.LengthExhausted, 3, true));
        Assert.False(EmptyBodyDiagnosis.RoutableToActionLoop(EmptyBodyCause.Unknown, 3, true));
    }

    [Fact]
    public void A4_定因短名词表锁定()
    {
        Assert.Equal("tool_call", EmptyBodyDiagnosis.CauseName(EmptyBodyCause.ToolCall));
        Assert.Equal("length_exhausted", EmptyBodyDiagnosis.CauseName(EmptyBodyCause.LengthExhausted));
        Assert.Equal("upstream_stop", EmptyBodyDiagnosis.CauseName(EmptyBodyCause.UpstreamStop));
        Assert.Equal("unknown", EmptyBodyDiagnosis.CauseName(EmptyBodyCause.Unknown));
    }

    // ---------- B. 文案: 必须带上游真实 finish_reason ----------

    [Fact]
    public void B1_工具调用文案带上游原因且不再断言预算()
    {
        var s = EmptyBodyDiagnosis.Banner(EmptyBodyCause.ToolCall, "tool_calls");
        Assert.Contains("finish_reason=tool_calls", s);
        Assert.DoesNotContain("输出预算", s);          // 误诊根治
        Assert.Contains("工具", s);
    }

    [Fact]
    public void B2_预算耗尽文案带上游原因()
    {
        var s = EmptyBodyDiagnosis.Banner(EmptyBodyCause.LengthExhausted, "length");
        Assert.Contains("finish_reason=length", s);
        Assert.Contains("输出预算", s);
    }

    [Fact]
    public void B3_未上报原因不得伪造()
    {
        Assert.Contains("(未上报)", EmptyBodyDiagnosis.Banner(EmptyBodyCause.Unknown, null));
        Assert.Contains("(未上报)", EmptyBodyDiagnosis.Banner(EmptyBodyCause.UpstreamStop, "  "));
    }

    [Fact]
    public void B4_文案与徽标前缀可拼接_且拼后不可回放()
    {
        foreach (var cause in new[] { EmptyBodyCause.ToolCall, EmptyBodyCause.LengthExhausted, EmptyBodyCause.UpstreamStop, EmptyBodyCause.Unknown })
        {
            var s = EmptyBodyDiagnosis.Banner(cause, "stop");
            Assert.StartsWith(": ", s);                                        // 前缀拼接契约
            var full = ModelQueueRouter.EmptyBodyBannerPrefix + s;
            Assert.StartsWith(ModelQueueRouter.EmptyBodyBannerPrefix, full);
            Assert.False(ModelQueueRouter.IsReplayableReply(full));            // 回放守卫仍识别为非实质答复
        }
    }

    // ---------- C. 源级钉死 (防回落) ----------

    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln"))) dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    private static string Flat(params string[] relative)
        => string.Join(' ', File.ReadAllText(Path.Combine(new[] { RepoRoot() }.Concat(relative).ToArray()))
            .Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));

    [Fact]
    public void C1_误诊文案不得回落_且定因接在调用点上()
    {
        var flat = Flat("src", "agent.modelqueue", "ModelQueueRouter.cs");
        Assert.DoesNotContain("推理过程占满了输出预算", flat);                 // 旧误诊 (R477 实证为假)
        Assert.Contains("EmptyBodyDiagnosis.Classify(resp.FinishReason", flat); // 定因接点
        Assert.Contains("empty_body_tool_calls_not_executed", flat);           // 工具调用未执行 ⇒ 可见失败
        Assert.Contains("retry_skipped", flat);                                // 跳重试必须落盘 (可机检)
        Assert.Contains("EmptyBodyDiagnosis.Banner(cause, retried.FinishReason ?? first.FinishReason)", flat);
    }

    [Fact]
    public void C2_因果id三层透传()
    {
        Assert.Contains("public string RequestId { get; set; }",
            Flat("src", "agent.modelqueue", "ModelQueueRouter.cs"));
        Assert.Contains("(\"request_id\", resp.RequestId)",
            Flat("src", "agent.modelqueue", "ModelQueueRouter.cs"));
        Assert.Contains("ResponseId = r.RequestId,",
            Flat("src", "agent", "modelqueue", "ModelQueueAdapter.cs"));
        var chain = Flat("src", "agent", "IndustrialAgentV2.cs");
        Assert.Contains("_replyRequestId = llmResponse.ResponseId ?? \"\";", chain);
        Assert.Contains("(\"request_id\", _replyRequestId)", chain);
        Assert.Contains("_replyRequestId = \"\";", chain);   // 逐轮清零 (禁跨轮串号)
    }
}
