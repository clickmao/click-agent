using agent.modelqueue;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.13.1 F1 — 兜底配置单测: 开关/校验/错误模板/序 (纯逻辑; Router 链由集成批测覆盖)。
/// </summary>
public class FallbackConfigTests
{
    private static QueueResponse Ok(string content) => new() { Success = true, Content = content };
    private static QueueResponse Fail(string err) => new() { Success = false, Error = err };

    [Fact]
    public void VerifyReply_Passes_Normal_Content()
    {
        var cfg = new FallbackConfig();
        Assert.True(cfg.VerifyReply(Ok("正常回答内容, 足够长。")));
    }

    [Fact]
    public void VerifyReply_Rejects_Short_Or_Error_Template()
    {
        var cfg = new FallbackConfig();
        Assert.False(cfg.VerifyReply(Ok("嗯"))); // 1ch < MinReplyChars=2
        Assert.True(cfg.VerifyReply(Ok("ok")));  // 2ch 合法短回复放行 (测试 Router_Consecutive 实证驱动)
        Assert.False(cfg.VerifyReply(Ok("HTTP 500: internal error"))); // 错误模板
        Assert.False(cfg.VerifyReply(Ok("未正常接收到prompt参数"))); // 真机 400 模板 (C07 实证)
        Assert.False(cfg.VerifyReply(Fail("boom")));
    }

    [Fact]
    public void VerifyDisabled_Passes_Any_Success()
    {
        var cfg = new FallbackConfig { VerifyFallbackReply = false };
        Assert.True(cfg.VerifyReply(Ok("HTTP 500 但校验关了")));
    }

    [Fact]
    public void Defaults_Match_User_Directive()
    {
        // 用户钦定默认: 启用兜底 + 性价比序 + 校验开:
        var cfg = new FallbackConfig();
        Assert.True(cfg.Enabled);
        Assert.Equal("cost_quality", cfg.Order);
        Assert.True(cfg.VerifyFallbackReply);
        Assert.True(cfg.PerRequestMaxFallbacks >= 2);
    }
}
