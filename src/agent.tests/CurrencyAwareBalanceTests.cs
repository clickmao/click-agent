using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.11.0 R15: 余额币种换算 + 排序降权 (真 bug: CNY 余额被当 USD 比价, 差 7.2 倍)
/// </summary>
public class CurrencyAwareBalanceTests
{
    [Fact]
    public void CurrencyToUsdRate_Defaults_And_Env_Override()
    {
        Assert.Equal(1.0, agent.modelqueue.TokenUsageService.CurrencyToUsdRate("USD"));
        Assert.Equal(1.0, agent.modelqueue.TokenUsageService.CurrencyToUsdRate(""));
        Assert.Equal(7.2, agent.modelqueue.TokenUsageService.CurrencyToUsdRate("CNY"));
        Environment.SetEnvironmentVariable("AGENTFRAMEWORK_FX_RATE_CNY_USD", "7.0");
        try
        {
            Assert.Equal(7.0, agent.modelqueue.TokenUsageService.CurrencyToUsdRate("CNY"));
        }
        finally
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_FX_RATE_CNY_USD", null);
        }
    }

    [Fact]
    public void RankCandidates_BalanceProbe_Insufficient_SinksScore()
    {
        var sched = new agent.modelqueue.ChannelScheduler();
        var catalog = new agent.modelqueue.ModelCatalog();
        catalog.Models.Add(new agent.modelqueue.ModelCatalogEntry
        {
            Id = "cheap-a", Provider = "provA", ApiKeyEnv = "K_A",
            PriceInPerM = 0.5, PriceOutPerM = 1.5, ReasoningScore = 9,
        });
        catalog.Models.Add(new agent.modelqueue.ModelCatalogEntry
        {
            Id = "cheap-b", Provider = "provB", ApiKeyEnv = "K_B",
            PriceInPerM = 0.5, PriceOutPerM = 1.5, ReasoningScore = 9,
        });
        Environment.SetEnvironmentVariable("K_A", "x");
        Environment.SetEnvironmentVariable("K_B", "x");
        try
        {
            // provB 余额不足 → 强降权; provA null=true 不动 → A 排第一
            sched.BalanceProbe = (provider, tokens) =>
                provider == "provB" ? ((double?)0.1, false) : ((double?)null, true);
            var ranked = sched.RankCandidates(catalog.Models, agent.modelqueue.TaskKindHint.General, 1000);
            Assert.Equal("cheap-a", ranked[0].Model.Id);
            Assert.True(ranked[0].TotalScore > ranked[1].TotalScore);
        }
        finally
        {
            Environment.SetEnvironmentVariable("K_A", null);
            Environment.SetEnvironmentVariable("K_B", null);
        }
    }
}
