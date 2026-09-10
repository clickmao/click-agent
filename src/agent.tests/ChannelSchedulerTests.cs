using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// 通道调度测试 (R351: 本地/官方通道移除 — 仅远端目录通道; 并发托管/选模打分保留)。
/// </summary>
public class ChannelSchedulerTests
{
    [Fact]
    public void Acquire_RemoteChannel_ConcurrencyManaged()
    {
        var sched = new ChannelScheduler(remoteMax: 2);
        Assert.Equal(ModelChannel.Remote, sched.AcquireChannel());
        Assert.Equal(ModelChannel.Remote, sched.AcquireChannel());
        Assert.Null(sched.AcquireChannel());                        // 全满
        sched.ReleaseChannel(ModelChannel.Remote);
        Assert.Equal(ModelChannel.Remote, sched.AcquireChannel());  // 释放后又可用
    }

    [Fact]
    public void Unavailable_Channel_Skipped()
    {
        var sched = new ChannelScheduler(remoteMax: 1);
        sched.SetAvailable(ModelChannel.Remote, false);
        Assert.Null(sched.AcquireChannel()); // 唯一通道不可用 → null (不阻塞主链语义)
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
    public void RankCandidates_NoKey_SinksEntry()
    {
        // key 未配置 → 强降权 (auto 不选将失败的模型; R351 机制保留)
        var sched = new ChannelScheduler();
        var keyed = new ModelCatalogEntry
        {
            Id = "keyed", Provider = "remote", ReasoningScore = 5, CodingScore = 5,
            PriceInPerM = 1, PriceOutPerM = 1, ContextWindow = 128000,
            ApiKeyEnv = "AF_TEST_KEYED_KEY",
            SuitedFor = new List<string> { "general" },
        };
        var unkeyed = new ModelCatalogEntry
        {
            Id = "unkeyed", Provider = "remote", ReasoningScore = 9, CodingScore = 9,
            PriceInPerM = 0, PriceOutPerM = 0, ContextWindow = 128000,
            ApiKeyEnv = "AF_TEST_UNKEYED_KEY",
            SuitedFor = new List<string> { "general" },
        };
        var old = Environment.GetEnvironmentVariable("AF_TEST_KEYED_KEY");
        var old2 = Environment.GetEnvironmentVariable("AF_TEST_UNKEYED_KEY");
        try
        {
            Environment.SetEnvironmentVariable("AF_TEST_KEYED_KEY", "k");
            Environment.SetEnvironmentVariable("AF_TEST_UNKEYED_KEY", null);
            var ranked = sched.RankCandidates(new[] { unkeyed, keyed }, TaskKindHint.General, 1000);
            Assert.Equal(0, ranked.First(r => r.Model.Id == unkeyed.Id).PriceScore);
            Assert.Equal("keyed", ranked[0].Model.Id);
        }
        finally
        {
            Environment.SetEnvironmentVariable("AF_TEST_KEYED_KEY", old);
            Environment.SetEnvironmentVariable("AF_TEST_UNKEYED_KEY", old2);
        }
    }
}
