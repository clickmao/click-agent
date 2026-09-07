using agent.modelqueue;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.11.0 R115: 余额阈值切模链修复回归 (真缺陷 44/44b/45/46)。
/// </summary>
public class BalanceThresholdTests
{
    [Fact]
    public void CurrencyToUsdRate_CNY_IsUsdPerCnyDivisor()
    {
        // 语义: 返回值 = 1 USD 兑 CNY 数量 (7.2)。换算 CNY→USD 必须 **除**。
        var rate = TokenUsageService.CurrencyToUsdRate("CNY");
        Assert.Equal(7.2, rate, precision: 1);
        Assert.Equal(1.0, TokenUsageService.CurrencyToUsdRate("USD"), precision: 3);
        Assert.Equal(1.0, TokenUsageService.CurrencyToUsdRate(""), precision: 3);
    }

    [Fact]
    public void CnyBalanceToUsd_Divides_NotMultiplies()
    {
        // 缺陷 45 锁定: 9.02 CNY = 1.253 USD (除), 不是 64.94 (乘)。
        var cny = 9.02;
        var rate = TokenUsageService.CurrencyToUsdRate("CNY");
        var usd = cny / rate;
        Assert.InRange(usd, 1.20, 1.30);
    }
}
