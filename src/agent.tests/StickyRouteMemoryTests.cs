using agent.exploration;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.13.1 F2 — 粘性路由记忆单测。
/// 用户钦定语义: 相似问题首用成功模型; 双门/三门判定 (相似+意图+实体指纹);
/// 形近意远 (同意图不同 URL) 不粘; TTL 过期; avoid 已知失败模型; 开关。
/// </summary>
public class StickyRouteMemoryTests
{
    private static float[] V(params float[] xs) => xs;
    private static readonly DateTime Now = new(2026, 9, 8, 12, 0, 0, DateTimeKind.Utc);

    [Fact]
    public void Similar_Question_Uses_Previously_Successful_Model()
    {
        var m = new StickyRouteMemory();
        m.Write(new RouteRecord
        {
            QuestionEmbedding = V(1, 0, 0), Intent = "search",
            EntityFingerprint = "url:example.com", ModelId = "glm-5.3-flash",
            Outcome = "success", CreatedAtUtc = Now.AddHours(-1),
        });
        var d = m.Decide("q", V(0.99f, 0.01f, 0), "search", "url:example.com", Now);
        Assert.True(d.Sticky);
        Assert.Equal("glm-5.3-flash", d.ModelId);
    }

    [Fact]
    public void Same_Intent_Different_Entity_Does_Not_Stick()
    {
        // T-R02 反向: "总结 https://a.com" vs "总结 https://b.com" — 意图同, 实体不同 = 不同任务:
        var m = new StickyRouteMemory();
        m.Write(new RouteRecord
        {
            QuestionEmbedding = V(1, 0), Intent = "search",
            EntityFingerprint = "url:a.com", ModelId = "glm-5.3-flash",
            Outcome = "success", CreatedAtUtc = Now.AddHours(-1),
        });
        var d = m.Decide("q", V(0.99f, 0.01f), "search", "url:b.com", Now);
        Assert.False(d.Sticky);
        Assert.False(d.Avoid);
    }

    [Fact]
    public void Known_Failure_Model_Is_Avoided()
    {
        var m = new StickyRouteMemory();
        m.Write(new RouteRecord
        {
            QuestionEmbedding = V(1, 0), Intent = "general",
            EntityFingerprint = "", ModelId = "deepseek-v4-flash",
            Outcome = "fail", CreatedAtUtc = Now.AddHours(-1),
        });
        var d = m.Decide("q", V(0.99f, 0.01f), "general", "", Now);
        Assert.True(d.Avoid);
        Assert.Equal("deepseek-v4-flash", d.ModelId);
        Assert.False(d.Sticky);
    }

    [Fact]
    public void Below_Threshold_Does_Not_Stick()
    {
        var m = new StickyRouteMemory();
        m.Write(new RouteRecord
        {
            QuestionEmbedding = V(1, 0), Intent = "general",
            EntityFingerprint = "", ModelId = "m1",
            Outcome = "success", CreatedAtUtc = Now.AddHours(-1),
        });
        var d = m.Decide("q", V(0.5f, 0.5f), "general", "", Now); // cos=0.707 < 0.80
        Assert.False(d.Sticky);
    }

    [Fact]
    public void Ttl_Expired_Does_Not_Stick()
    {
        var cfg = new StickyRouteConfig { StickyTtlHours = 72 };
        var m = new StickyRouteMemory(cfg);
        m.Write(new RouteRecord
        {
            QuestionEmbedding = V(1, 0), Intent = "general",
            EntityFingerprint = "", ModelId = "m1",
            Outcome = "success", CreatedAtUtc = Now.AddHours(-100), // 超 TTL
        });
        var d = m.Decide("q", V(1, 0), "general", "", Now);
        Assert.False(d.Sticky);
    }

    [Fact]
    public void Disabled_Config_Never_Sticks()
    {
        var cfg = new StickyRouteConfig { Enabled = false };
        var m = new StickyRouteMemory(cfg);
        m.Write(new RouteRecord
        {
            QuestionEmbedding = V(1, 0), Intent = "general",
            EntityFingerprint = "", ModelId = "m1",
            Outcome = "success", CreatedAtUtc = Now.AddHours(-1),
        });
        Assert.False(m.Decide("q", V(1, 0), "general", "", Now).Sticky);
    }

    [Fact]
    public void Most_Recent_Success_Wins_On_Multiple_Hits()
    {
        var m = new StickyRouteMemory();
        m.Write(new RouteRecord
        {
            QuestionEmbedding = V(1, 0), Intent = "general",
            EntityFingerprint = "", ModelId = "old-model",
            Outcome = "success", CreatedAtUtc = Now.AddHours(-10),
        });
        m.Write(new RouteRecord
        {
            QuestionEmbedding = V(0.98f, 0.02f), Intent = "general",
            EntityFingerprint = "", ModelId = "new-model",
            Outcome = "success", CreatedAtUtc = Now.AddHours(-1),
        });
        var d = m.Decide("q", V(1, 0), "general", "", Now);
        Assert.Equal("new-model", d.ModelId);
    }
}
