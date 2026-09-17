using agent.llamacpp;
using agent.modelqueue;
using Xunit;
namespace agent.tests;

/// <summary>
/// R411 J4: 本地 K2b 口径（<see cref="LocalSessionCacheLedger"/>）—— 纯逻辑判定，不需要 llama-server。
///
/// 实测锚点（独立实现 /apply-template + /tokenize + /completion 对账，见 eval/rover/r411/semantics.json）:
///   冷启: 渲染 496 tok / tokens_evaluated 497 / prompt_n 497 / cache_n 0
///   热轮: 渲染 529 tok / tokens_evaluated 530 / prompt_n 18  / cache_n 512
///   ⇒ **tokens_evaluated = 总长**（含 BOS），prompt_n = 重算数；命中 512/530 = 96.60% &lt; 97% ⇒ 越线是真的。
///
/// 判据（开跑前登记）:
///   J4a 首轮不判: 首轮无「可复用部分」⇒ 记 Unknown(-1) 且不越线（与「命中 0」严格区分）
///   J4b 双条件: 携带复用率 ≥97% **且** 前缀绝对长度 ≥4224 才算达标（R410: 比值不是 KPI）
///   J4c 弃权: 命中 &gt; 可复用上限 ⇒ 记 -1 且不出判决（口径不符不得硬套）
///   J4d 未上报: cache_n 缺失 ⇒ Unknown(-1)，不得冒充 0
///   J4e 隔离: 两个会话互不污染
///   J4f 达标: 长前缀(4464) + 命中全复用 ⇒ 复用率 1.0 且不越线
/// </summary>
public sealed class LocalSessionCacheLedgerTests
{
    private const int Required = 4224;   // PromptCacheKpi.PrefixTokensNeededFor(0.97)

    [Fact]
    public void FirstTurn_NotJudged_NotZeroHit()
    {
        var ledger = new LocalSessionCacheLedger();
        var obs = ledger.Observe("s", 1, 497, 0);

        Assert.Equal(0, obs.CarryOverTokens);
        Assert.Equal(-1, obs.CarryOverReuse);
        Assert.False(obs.RedlineApplies);
        Assert.False(obs.Violated);
        Assert.Equal(1, ledger.NotApplicable);
        Assert.Equal(0, ledger.Violations);
    }

    [Fact]
    public void ShortPrefix_ReuseIsFineButAbsoluteLengthFails()
    {
        var ledger = new LocalSessionCacheLedger();
        ledger.Observe("s", 1, 497, 0);                                   // 冷启 497
        var hot = ledger.Observe("s", 2, 530, 512, carryOverCeiling: 513); // 热轮: 命中 512

        Assert.Equal(513, hot.CarryOverTokens);
        Assert.Equal(0.9981, hot.CarryOverReuse);                         // 512/513；携带复用率达标
        Assert.Equal(0.966, hot.SessionReuseRatio);                       // 但整体只有 96.6%
        Assert.Equal(497, hot.PrefixTokens);
        Assert.False(hot.PrefixLengthSatisfied);
        Assert.True(hot.Violated);                                        // ★ 绝对长度不达标 ⇒ 越线
        Assert.NotNull(hot.Diagnosis);
        Assert.Contains(Required.ToString(), hot.Diagnosis);               // 诊断里必须给出所需绝对长度
        Assert.Contains("绝对长度", hot.Diagnosis);
        Assert.Equal(1, ledger.Violations);
    }

    [Fact]
    public void LongPrefix_FullReuse_Passes()
    {
        var ledger = new LocalSessionCacheLedger();
        ledger.Observe("s", 1, 4464, 0);                                   // 长前缀冷启
        var hot = ledger.Observe("s", 2, 4497, 4480, carryOverCeiling: 4480);

        Assert.True(hot.PrefixLengthSatisfied);
        Assert.Equal(1.0, hot.CarryOverReuse);
        Assert.False(hot.Violated);
        Assert.Null(hot.Diagnosis);
        Assert.Equal(0, ledger.Violations);
    }

    [Fact]
    public void HitBeyondCeiling_Abstains_NoVerdict()
    {
        var ledger = new LocalSessionCacheLedger();
        ledger.Observe("s", 1, 100, 0);
        var obs = ledger.Observe("s", 2, 120, 150);        // 命中 150 > 可复用上限 100 ⇒ 口径不符

        Assert.Equal(-1, obs.CarryOverReuse);
        Assert.False(obs.RedlineApplies);
        Assert.False(obs.Violated);                        // 不硬套判决
        Assert.Equal(1, ledger.Abstained);
        Assert.Equal(0, ledger.Violations);
    }

    [Fact]
    public void UnreportedHit_IsUnknown_NotZero()
    {
        var ledger = new LocalSessionCacheLedger();
        ledger.Observe("s", 1, 497, 0);
        var obs = ledger.Observe("s", 2, 530, -1);         // provider 未上报

        Assert.Equal(-1, obs.CarryOverReuse);
        Assert.Equal(-1, obs.SessionReuseRatio);
        Assert.False(obs.Violated);
        Assert.Equal(530, obs.RecomputedTokens);           // 未上报 ⇒ 视作全部重算（不假装命中）
    }

    [Fact]
    public void Sessions_AreIsolated()
    {
        var ledger = new LocalSessionCacheLedger();
        ledger.Observe("s-a", 1, 4464, 0);
        var firstB = ledger.Observe("s-b", 1, 19, 0);      // 另一个会话的首轮

        Assert.Equal(0, firstB.CarryOverTokens);
        Assert.Equal(-1, firstB.CarryOverReuse);
        Assert.Equal(4464, ledger.PrefixTokensFor("s-a"));
        Assert.Equal(19, ledger.PrefixTokensFor("s-b"));
    }

    [Fact]
    public void NoSessionKey_IsNotRemembered()
    {
        var ledger = new LocalSessionCacheLedger();
        ledger.Observe(null, 1, 497, 0);
        var second = ledger.Observe(null, 2, 530, 512);

        Assert.Equal(0, ledger.LastPromptTokensFor(null));
        Assert.Equal(0, second.CarryOverTokens);           // 无会话归属 ⇒ 不逐轮记账
        Assert.Equal(2, ledger.Observations);
    }
}
