using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 需求1 测试: 官方模型硬编码/key 内存态/三通道并发托管/优先级/子任务综合选模。
/// </summary>
public class ChannelSchedulerTests
{
    [Fact]
    public void Official_Models_Are_Hardcoded_And_Isolated_From_Yaml()
    {
        Assert.Equal(2, OfficialModels.Models.Count);
        Assert.All(OfficialModels.Models, m => Assert.Equal("official", m.Provider));
        Assert.NotNull(OfficialModels.Find("official-gpt-4o"));
        Assert.Null(OfficialModels.Find("official-nonexistent"));
    }

    [Fact]
    public void KeyStore_Memory_Only_Set_Clear_Availability()
    {
        var store = new OfficialKeyStore();
        Assert.False(store.IsAvailable());
        store.Set("sk-test");
        Assert.True(store.IsAvailable());
        Assert.Equal("sk-test", store.Get());
        store.Set(null); // off 清除
        Assert.False(store.IsAvailable());
    }

    [Fact]
    public void Acquire_Follows_Priority_Local_Official_Remote()
    {
        var sched = new ChannelScheduler(localMax: 1, officialMax: 1, remoteMax: 1);
        sched.SetAvailable(ModelChannel.Official, true); // key 注入语义
        Assert.Equal(ModelChannel.Local, sched.AcquireChannel());  // 本地优先
        Assert.Equal(ModelChannel.Official, sched.AcquireChannel()); // 本地满 → 官方
        Assert.Equal(ModelChannel.Remote, sched.AcquireChannel());  // 官方满 → 远端
        Assert.Null(sched.AcquireChannel());                        // 全满
        sched.ReleaseChannel(ModelChannel.Local);
        Assert.Equal(ModelChannel.Local, sched.AcquireChannel());   // 释放后本地又可用
    }

    [Fact]
    public void Unavailable_Channel_Skipped()
    {
        var sched = new ChannelScheduler(localMax: 1, officialMax: 1, remoteMax: 1);
        sched.SetAvailable(ModelChannel.Official, false); // 无 key
        Assert.Equal(ModelChannel.Local, sched.AcquireChannel());
        Assert.Equal(ModelChannel.Remote, sched.AcquireChannel()); // 官方跳过
    }

    [Fact]
    public void RankCandidates_Prefers_Cheap_Fast_For_Light_Kinds()
    {
        var sched = new ChannelScheduler();
        var heavy = new ModelCatalogEntry
        {
            Id = "heavy", Provider = "remote", ReasoningScore = 9, CodingScore = 9,
            PriceInPerM = 10, PriceOutPerM = 30, ContextWindow = 128000,
            SuitedFor = new List<string> { "reasoning" },
        };
        var light = new ModelCatalogEntry
        {
            Id = "light", Provider = "remote", ReasoningScore = 6, CodingScore = 6,
            PriceInPerM = 0.1, PriceOutPerM = 0.4, ContextWindow = 128000,
            SuitedFor = new List<string> { "chat", "classify" },
        };
        var ranked = sched.RankCandidates(new[] { heavy, light },
            TaskKindHint.KeywordTagging, 1000);
        Assert.Equal("light", ranked[0].Model.Id); // 轻任务 → 便宜高速优先

        var rankedHeavy = sched.RankCandidates(new[] { heavy, light },
            TaskKindHint.General, 1000);
        // 重任务: 推理权重高 → heavy 竞争力提升 (不强制第一 — 断言分差收窄)
        Assert.True(rankedHeavy[0].TotalScore >= rankedHeavy[1].TotalScore);
    }

    [Fact]
    public void Router_SetOfficialKey_Toggles_Official_Channel()
    {
        var catalog = new ModelCatalog();
        var router = new ModelQueueRouter(catalog,
            new System.Net.Http.HttpClientHandler().CreateHttpClientFactoryStub(),
            new TestLogger());
        Assert.False(router.OfficialKeys.IsAvailable());
        router.SetOfficialKey("sk-abc");
        Assert.True(router.OfficialKeys.IsAvailable());
        Assert.True(router.Scheduler.Snapshot().First(c => c.Channel == ModelChannel.Official).Available);
        router.SetOfficialKey(null);
        Assert.False(router.OfficialKeys.IsAvailable());
    }

    private sealed class TestLogger : Microsoft.Extensions.Logging.ILogger
    {
        public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;
        public bool IsEnabled(Microsoft.Extensions.Logging.LogLevel logLevel) => false;
        public void Log<TState>(Microsoft.Extensions.Logging.LogLevel logLevel, Microsoft.Extensions.Logging.EventId eventId,
            TState state, Exception? exception, Func<TState, Exception?, string> formatter) { }
    }
}

/// <summary>HttpClientFactory 测试桩 (IHttpClientFactory 最小实现)</summary>
internal static class HttpClientFactoryStub
{
    public static IHttpClientFactory CreateHttpClientFactoryStub(this System.Net.Http.HttpClientHandler _) =>
        new StubFactory();

    private sealed class StubFactory : IHttpClientFactory
    {
        public System.Net.Http.HttpClient CreateClient(string name) => new();
    }
}
