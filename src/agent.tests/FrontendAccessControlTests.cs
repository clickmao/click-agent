using agent.frontendapi;
using Xunit;

namespace agent.tests;

/// <summary>R358 (工业级 #2/#3): FrontendApi 鉴权 + 令牌桶限流 + 并发上限。</summary>
public class FrontendAccessControlTests
{


    [Fact]
    public void 默认_随机token生成_非空()
    {
        var a = new FrontendAccessControl();
        Assert.True(a.AuthEnabled);
        Assert.DoesNotContain("(auth=0", a.TokenHex);
        // 两次实例 token 独立
        var b = new FrontendAccessControl();
        Assert.NotEqual(a.TokenHex, b.TokenHex);
    }

    [Fact]
    public void token校验_正确通过_错误拒绝_空拒绝()
    {
        var a = new FrontendAccessControl(tokenOverride: "my-token-123");
        Assert.True(a.ValidateToken("my-token-123"));
        Assert.False(a.ValidateToken("my-token-123x"));
        Assert.False(a.ValidateToken(""));
        Assert.False(a.ValidateToken(null));
    }

    [Fact]
    public void 随机token_hex展示_校验原文()
    {
        // 随机 token: TokenHex 是展示形式 (客户端拿到的就是它) — 校验 hex 原文
        var a = new FrontendAccessControl();
        var hex = a.TokenHex;
        Assert.True(a.ValidateToken(hex));
        Assert.False(a.ValidateToken(hex + "x"));
    }

    [Fact]
    public void env注入_token生效()
    {
        var a = new FrontendAccessControl(tokenOverride: "my-secret-token");
        Assert.True(a.ValidateToken("my-secret-token"));
        Assert.False(a.ValidateToken("other"));
    }

    [Fact]
    public void auth0显式关闭_放行一切()
    {
        var a = new FrontendAccessControl(authDisabledOverride: true);
        Assert.False(a.AuthEnabled);
        Assert.True(a.ValidateToken(null));
        Assert.True(a.ValidateToken("anything"));
    }

    [Fact]
    public void 令牌桶_突发耗尽后拒绝_随时间恢复()
    {
        var a = new FrontendAccessControl(requestsPerSecond: 1000, burstCapacity: 3, maxConcurrent: 100);
        Assert.True(a.TryAcquire()); a.Release();
        Assert.True(a.TryAcquire()); a.Release();
        Assert.True(a.TryAcquire()); a.Release();
        Assert.False(a.TryAcquire()); // 桶空
        Thread.Sleep(5); // ~5 个令牌补充 (1000/s)
        Assert.True(a.TryAcquire()); a.Release();
    }

    [Fact]
    public void 并发上限_超限拒绝_释放后恢复()
    {
        var a = new FrontendAccessControl(requestsPerSecond: 100000, burstCapacity: 100, maxConcurrent: 2);
        Assert.True(a.TryAcquire());
        Assert.True(a.TryAcquire());
        Assert.False(a.TryAcquire()); // 满
        a.Release();
        Assert.True(a.TryAcquire()); // 释放后可再入
        a.Release();
    }
}
