using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R476 (用户钦定「一轮任务」判据 + 97% 红线) 机检: **红线判定分档化**。
///
/// 缘由 (R469 已收口): 命中率 = 1 − 新/前缀, 而**用户轮长度不可压** (压了就是改用户输入),
/// 故结构上限 = prefix/(prefix + 用户轮 + 承接21)。长档上限 < 97% ⇒ 单值 97% 判据对长轮
/// **结构性不可达**, 只能误判。R476 判据改为「逐档目标 = min(红线, 结构上限)」+ 达成轮占比。
///
/// 夹具口径 = `eval/rover/r469/hit-ceiling.json` (400 条真实轮; 由 r476 器具机检逐值复算),
/// 本文件把同一批数字**烙进产品单测**, 使器具与源码任何一侧漂移都变红。
/// 负控: B5/B7 —— 单值口径必判越线的轮, 分档口径判达标; 未上报(-1) 必**不**计入达成。
/// </summary>
public class PromptCacheBandTests
{
    // ── 夹具 (逐字取自 eval/rover/r469/hit-ceiling.json) ──
    private static readonly double[] MedianUserTok = { 11.0, 51.0, 138.0, 300.0 };
    private static readonly int[] BandTurns = { 130, 68, 64, 138 };
    private static readonly bool[] Reachable97 = { true, true, false, false };
    private static readonly int[] FixturePrefixes = { 2110, 3000, 4000 };
    private static readonly double[,] FixtureCeilings =
    {
        { 0.9851, 0.9670, 0.9299, 0.8680 },   // prefix 2110 (R467 实测)
        { 0.9894, 0.9766, 0.9497, 0.9033 },   // prefix 3000 (假设档, 仅作敏感性)
        { 0.9921, 0.9823, 0.9618, 0.9257 },   // prefix 4000 (假设档, 仅作敏感性)
    };
    private static readonly double[] FixtureNeededPrefix = { 1034.7, 2328.0, 5141.0, 10379.0 };

    private const double FixtureRedline = 0.97;

    // ── B1 档边界 (逐值, 边界 ±1 双向) ──
    [Theory]
    [InlineData(-1, -1)]
    [InlineData(0, 0)]
    [InlineData(30, 0)]
    [InlineData(31, 1)]
    [InlineData(93, 1)]
    [InlineData(94, 2)]
    [InlineData(200, 2)]
    [InlineData(201, 3)]
    [InlineData(10000, 3)]
    [InlineData(int.MaxValue, 3)]
    public void B1_BandOf_ExactEdges(int userTurnTokens, int expected)
        => Assert.Equal(expected, PromptCacheRedline.BandOf(userTurnTokens));

    [Fact]
    public void B1b_BandLabel_MatchesFixtureKeys()
    {
        Assert.Equal("0-30", PromptCacheRedline.BandLabel(0));
        Assert.Equal("31-93", PromptCacheRedline.BandLabel(1));
        Assert.Equal("94-200", PromptCacheRedline.BandLabel(2));
        Assert.Equal("201+", PromptCacheRedline.BandLabel(3));
        Assert.Equal("unknown", PromptCacheRedline.BandLabel(-1));
        Assert.Equal("unknown", PromptCacheRedline.BandLabel(4));
    }

    // ── B2 结构上限逐值与 r469 夹具一致 (端口保真; 公式 = prefix/(prefix+u+21)) ──
    [Fact]
    public void B2_CeilingFor_MatchesR469Fixture_ValueByValue()
    {
        for (var p = 0; p < FixturePrefixes.Length; p++)
        {
            for (var b = 0; b < MedianUserTok.Length; b++)
            {
                var got = Math.Round(PromptCacheRedline.CeilingFor(FixturePrefixes[p], (int)MedianUserTok[b]), 4);
                Assert.Equal(FixtureCeilings[p, b], got, 4);
            }
        }
        Assert.Equal(PromptCacheRedline.TurnOverheadTokens, 21);   // 夹具隐含常数 (承接上界)
    }

    [Fact]
    public void B2b_PrefixTokensNeededForBand_MatchesR469Fixture()
    {
        for (var b = 0; b < MedianUserTok.Length; b++)
        {
            var got = PromptCacheRedline.PrefixTokensNeededForBand((int)MedianUserTok[b], FixtureRedline);
            Assert.Equal(FixtureNeededPrefix[b], Math.Round(got, 1), 1);
        }
    }

    // ── B3 可达性: 短档目标=红线, 长档目标=上限 (夹具 reachable_97 逐档一致) ──
    [Fact]
    public void B3_Reachable97_MatchesFixture_AndTargetCapsAtCeiling()
    {
        Assert.Equal(FixtureRedline, PromptCacheRedline.Threshold, 6);   // 红线一字未动
        for (var b = 0; b < MedianUserTok.Length; b++)
        {
            var u = (int)MedianUserTok[b];
            // 夹具语义: reachable_97 = 在夹具前缀集 {2110,3000,4000} 中**存在**一个可达 97% 的前缀
            var reachable = FixturePrefixes.Any(p => PromptCacheRedline.TargetFor(p, u) >= FixtureRedline);
            Assert.Equal(Reachable97[b], reachable);
            // 目标 ≡ min(红线, 该前缀上限) —— 对夹具每一个前缀逐一成立 (禁只查一个前缀)
            foreach (var p in FixturePrefixes)
                Assert.Equal(Math.Min(FixtureRedline, Math.Round(PromptCacheRedline.CeilingFor(p, u), 6)),
                             Math.Round(PromptCacheRedline.TargetFor(p, u), 6), 6);
            // 短档: 存在前缀使目标 = 红线 (未被上限压低); 长档: 任何前缀都到不了红线
            Assert.Equal(Reachable97[b], FixturePrefixes.Any(p => PromptCacheRedline.TargetFor(p, u) >= FixtureRedline));
        }
        Assert.Equal(400, BandTurns.Sum());   // 夹具样本量一致 (130+68+64+138)
    }

    // ── B4 单调性 (方向性负控: 反号即红) ──
    [Fact]
    public void B4_Monotonicity()
    {
        var prev = -1d;
        foreach (var u in new[] { 0, 11, 51, 138, 300, 1000 })
        {
            var c = PromptCacheRedline.CeilingFor(2110, u);
            Assert.True(c < prev || prev < 0, $"上限必须随用户轮增大而下降 (u={u})");
            prev = c;
        }
        Assert.True(PromptCacheRedline.CeilingFor(4000, 51) > PromptCacheRedline.CeilingFor(2110, 51));
        Assert.True(PromptCacheRedline.PrefixTokensNeededForBand(300, 0.97) > PromptCacheRedline.PrefixTokensNeededForBand(11, 0.97));
    }

    // ── B5 负控: 单值 97% 口径对长档必判越线, 而该轮其实**已在上限** ⇒ 旧口径=误判 ──
    [Fact]
    public void B5_SingleValueRedline_MisjudgesLongBand_ThatBandJudgeCallsAtTarget()
    {
        const int u = 300;
        const int cacheable = 2110;
        const int prompt = cacheable + u + 21;
        var rate = Math.Round(cacheable / (double)prompt, 4);   // = 0.8680 = 结构上限

        // 旧口径 (单值 97%): 判越线 —— 这是 R469 指出的结构性误判
        Assert.True(PromptCacheRedline.Violated(2, cacheable, rate));
        // 新口径 (分档): 已达该档上限 ⇒ at_target (被结构而非被实现判红)
        Assert.Equal(PromptCacheRedline.BandVerdict.AtTarget,
            PromptCacheRedline.JudgeBand(2, cacheable, cacheable, u, rate));
        // 同一轮的实测通道 (growth=u+21) 必须给同一结论
        Assert.Equal(PromptCacheRedline.BandVerdict.AtTarget,
            PromptCacheRedline.JudgeByGrowth(2, cacheable, prompt, rate));
    }

    // ── B6 四态 + 容差 (64 token 对齐损耗 = 正常, 不得判红) ──
    [Fact]
    public void B6_VerdictStates_And_AlignmentTolerance()
    {
        const int cacheable = 2110;
        var tol = PromptCacheRedline.ToleranceFor(cacheable);   // 64/2110 = 0.0303
        Assert.Equal(64d / 2110d, tol, 9);

        // 长档 (u=300, 上限 0.868): 差一个容差以内 ⇒ at_target
        Assert.Equal(PromptCacheRedline.BandVerdict.AtTarget,
            PromptCacheRedline.JudgeBand(2, cacheable, cacheable, 300, 0.868 - tol / 2));
        // 掉到上限下方超过容差 ⇒ 有结构空间可修
        Assert.Equal(PromptCacheRedline.BandVerdict.BelowCeiling,
            PromptCacheRedline.JudgeBand(2, cacheable, cacheable, 300, 0.868 - 2 * tol));
        // 短档 (u=11, 目标=红线 0.97): 未达 ⇒ below_target
        Assert.Equal(PromptCacheRedline.BandVerdict.BelowTarget,
            PromptCacheRedline.JudgeBand(2, cacheable, cacheable, 11, 0.90));
        // 首轮 (无"需要命中"面) ⇒ not_applicable
        Assert.Equal(PromptCacheRedline.BandVerdict.NotApplicable,
            PromptCacheRedline.JudgeBand(1, 0, cacheable, 11, 0.99));
    }

    // ── B7 负控: 未上报(-1) 禁按 0 计入达成率 ──
    [Fact]
    public void B7_UnreportedRate_NeverCountsAsZeroOrPass()
    {
        Assert.Equal(PromptCacheRedline.BandVerdict.Unreported,
            PromptCacheRedline.JudgeBand(2, 2110, 2110, 11, PromptCacheKpi.Unknown));
        var f = PromptCacheRedline.BandFields(2, 2110, 2320, PromptCacheKpi.Unknown);
        Assert.Equal(PromptCacheRedline.BandVerdict.Unreported, f[6].Value);
        Assert.Equal(PromptCacheKpi.Unknown, (double)f[5].Value!);   // margin 未上报, 不是 0
        Assert.NotEqual(0d, (double)f[5].Value!);
    }

    // ── B8 遥测口径声明: growth 是用户轮的**上偏代理** ⇒ 必须显式标 source; 首轮档未知 ──
    [Fact]
    public void B8_BandFields_DeclareBandSource()
    {
        // 首轮: cacheable=0 ⇒ 档/上限/目标全部 unknown (禁把首轮当短档)
        var first = PromptCacheRedline.BandFields(1, 0, 1900, PromptCacheKpi.Unknown);
        Assert.Equal(-1, (int)first[0].Value!);
        Assert.Equal(PromptCacheRedline.BandSourceUnknown, first[1].Value);
        Assert.Equal(PromptCacheKpi.Unknown, (int)first[2].Value!);
        Assert.Equal(PromptCacheKpi.Unknown, (double)first[3].Value!);

        // 第 2 轮: growth = 2320 - 2110 = 210 ⇒ 档 3 (上偏代理, 用户轮实际 ≤ 210)
        var second = PromptCacheRedline.BandFields(2, 2110, 2320, 0.85);
        Assert.Equal(3, (int)second[0].Value!);
        Assert.Equal(PromptCacheRedline.BandSourceGrowthProxy, second[1].Value);
        Assert.Equal(210, (int)second[2].Value!);
        Assert.Equal(Math.Round(2110d / 2320d, 4), (double)second[3].Value!, 6);
        Assert.Equal(PromptCacheRedline.BandVerdict.BelowCeiling, second[6].Value);

        // 字段顺序与文档/器具同序 (禁插队)
        Assert.Equal(new[] { "cache_band", "cache_band_source", "cache_band_growth", "cache_ceiling", "cache_target", "cache_margin", "cache_band_verdict" },
            second.Select(x => x.Key).ToArray());
    }

    // ── B9 诊断面必须带分档行, 且用户轮未知时**不猜档** ──
    [Fact]
    public void B9_BandLine_NeverGuessesBand()
    {
        var known = PromptCacheRedline.BandLine(2431, 2110, 300);
        Assert.Contains("档 201+", known);
        Assert.Contains("结构上限 86.80%", known);
        Assert.Contains("不可压用户轮", known);

        var unknown = PromptCacheRedline.BandLine(2431, 2110, -1);
        Assert.Contains("档未知", unknown);
        Assert.Contains("禁按 0 冒充短档", unknown);

        var diag = PromptCacheRedline.Diagnose(2, 2431, 2110, 1840, 591, 2110);
        Assert.Contains("分档:", diag);
    }
}
