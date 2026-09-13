using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R380 (用户钦定**口径修订**, 首要 KPI) 机检:
/// 命中率**只算"需要命中的部分"** —— 本轮新增不计入 (新增必然不命中, 计入即稀释指标)。
///   有效命中率 = hit / min(本轮 prompt, 上一轮同会话 prompt); 会话首轮不适用 (-1)。
/// 红线: 多轮会话第 2 轮起 ≥90% (目标 98~99%); 越线必须查因并修复 (诊断须含数值 + 根因清单)。
/// </summary>
public class PromptCacheRedlineTests
{
    [Fact]
    public void 口径_分母只算需要命中的部分_本轮新增不计入()
    {
        // 真机 mt_fix4 轮 2: 上轮 981, 本轮 1356, 命中 896 → 有效命中率 0.9134
        var cacheable = PromptCacheKpi.CacheableTokens(1356, 981);
        Assert.Equal(981, cacheable);
        Assert.Equal(0.9134, PromptCacheKpi.EffectiveHitRate(896, cacheable));
        // 旧口径 (含本轮新增) = 896/(896+460) = 0.6608 —— 仅参考, 不作判定
        Assert.Equal(0.6608, PromptCacheKpi.HitRate(896, 460));
    }

    [Fact]
    public void 口径_会话首轮无需要命中部分_不适用而非零()
    {
        Assert.Equal(0, PromptCacheKpi.CacheableTokens(981, 0));
        Assert.Equal(-1d, PromptCacheKpi.EffectiveHitRate(128, 0));
        Assert.Equal(-1d, PromptCacheKpi.EffectiveHitRate(128, PromptCacheKpi.CacheableTokens(981, 0)));
    }

    [Fact]
    public void 口径_prompt缩短时取min_比率不得超1()
    {
        var cacheable = PromptCacheKpi.CacheableTokens(500, 1200);
        Assert.Equal(500, cacheable);
        Assert.True(PromptCacheKpi.EffectiveHitRate(500, cacheable) <= 1.0);
    }

    [Fact]
    public void 未上报不冒充零命中()
    {
        Assert.Equal(-1d, PromptCacheKpi.EffectiveHitRate(null, 981));
        Assert.Equal(-1d, PromptCacheKpi.EffectiveHitRate(-1, 981));
        Assert.Equal(-1d, PromptCacheKpi.HitRate(null, 100));
    }

    [Fact]
    public void 红线_第2轮起低于95判定越线_首轮与无分母不判定()
    {
        Assert.Equal(0.95, PromptCacheRedline.Threshold);
        Assert.True(PromptCacheRedline.Violated(2, 981, 0.9499));
        Assert.False(PromptCacheRedline.Violated(2, 981, 0.95));
        Assert.False(PromptCacheRedline.Violated(1, 981, 0.10));   // 首轮冷启动
        Assert.False(PromptCacheRedline.Violated(2, 0, 0.10));     // 无"需要命中"部分
        Assert.False(PromptCacheRedline.Violated(3, 981, -1));     // 未上报
    }

    [Fact]
    public void 越线必查_诊断须给数值与四类根因清单()
    {
        var d = PromptCacheRedline.Diagnose(3, 1767, 1356, 700, 1067, 1356);
        Assert.Contains("越线", d);
        Assert.Contains("需要命中=1356", d);
        Assert.Contains("本轮新增=411", d);
        Assert.Contains("缺口=656", d);
        Assert.Contains("messages[0]", d);
        Assert.Contains("追加式回放", d);
        Assert.Contains("SentContent", d);
        Assert.Contains("增量", d);
        Assert.Contains("64 token", d);
    }

    [Fact]
    public void 负向控制_旧口径会把达标轮误判为越线()
    {
        // 真机 mt_fix4 轮 2: 旧口径 0.6608 (含本轮新增 375 token) → 会误判越线;
        // 新口径 0.9134 → 达标。断言两者方向相反, 证明口径修正是判定成立的前提。
        var cacheable = PromptCacheKpi.CacheableTokens(1356, 981);
        var oldRate = PromptCacheKpi.HitRate(896, 460);
        var newRate = PromptCacheKpi.EffectiveHitRate(896, cacheable);
        // 旧口径 0.6608 把"本轮新增"也算进分母 → 把结构已达极限的轮次误读成灾难性失败
        Assert.True(oldRate < 0.70, $"旧口径 {oldRate} 严重偏低 (含本轮新增 375 token)");
        // 新口径 0.9134: 该前缀的**理论上限就是** 0.9134 (981 → 上限 896)
        Assert.Equal(896, PromptCacheKpi.HitCeiling(cacheable));
        Assert.Equal(0.9134, newRate);
    }

    [Fact]
    public void 真机基线_95红线_当前越线且命中恰为理论上限()
    {
        // 真机 mt_fix4 (R379 结构修复后) 实测三元组: (本轮 prompt, hit, 上轮 prompt)
        var rows = new[] { (1356, 896, 981), (1767, 1280, 1356) };
        var turn = PromptCacheRedline.MinTurn;
        foreach (var (pt, hit, last) in rows)
        {
            var cacheable = PromptCacheKpi.CacheableTokens(pt, last);
            var rate = PromptCacheKpi.EffectiveHitRate(hit, cacheable);
            // ① 结构修复已到极限: 实测命中 == 该前缀的理论上限 (最后一个完整单元不计入)
            Assert.Equal(PromptCacheKpi.HitCeiling(cacheable), hit);
            Assert.Equal(896, PromptCacheKpi.HitCeiling(981));
            // ② 以 95% 红线判定: 前缀不足 → 越线 (这是**诚实**的当前状态, 不是回归)
            Assert.True(PromptCacheRedline.Violated(turn, cacheable, rate),
                $"前缀 {cacheable} 的上限 {PromptCacheKpi.HitCeiling(cacheable)} 不足以达 95% → 应判越线");
            turn++;
        }
    }

    [Fact]
    public void 达标态_前缀达到所需量级则95红线可通过()
    {
        // 算术 (最坏对齐稳健界): 95% ⇒ 前缀 ≥ 2496 token (39 单元); 98% ⇒ ≥ 6336; 90% ⇒ ≥ 1216
        Assert.Equal(2496, PromptCacheKpi.PrefixTokensNeededFor(0.95));
        Assert.Equal(6336, PromptCacheKpi.PrefixTokensNeededFor(0.98));
        Assert.Equal(1216, PromptCacheKpi.PrefixTokensNeededFor(0.90));
        // FP 边界族 (防"多算一个单元"复发: 1.9/0.1 这类商正好是整数但双精度有噪声)
        Assert.Equal(0, PromptCacheKpi.PrefixTokensNeededFor(1.0));
        Assert.Equal(192, PromptCacheKpi.PrefixTokensNeededFor(0.50));
        Assert.Equal(448, PromptCacheKpi.PrefixTokensNeededFor(0.75));
        Assert.Equal(576, PromptCacheKpi.PrefixTokensNeededFor(0.80));
        Assert.Equal(2496, PromptCacheKpi.PrefixTokensNeededFor(0.95));
        Assert.Equal(1216, PromptCacheKpi.PrefixTokensNeededFor(0.90));
        foreach (var t in new[] { 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99 })
        {
            var need = PromptCacheKpi.PrefixTokensNeededFor(t);
            // 带内最坏对齐也必须达线 (稳健界定义本身)
            for (var extra = 0; extra < 128; extra++)
            {
                var p2 = need + extra;
                var r2 = PromptCacheKpi.EffectiveHitRate(PromptCacheKpi.HitCeiling(p2), p2);
                Assert.True(r2 >= t, $"target={t} 前缀 {p2} → {r2} 应 ≥ {t}");
            }
        }
        // 真机达标态 (mt_fix5): 前缀 2001 → 上限 1920 → 1920/2001 = 0.9595 ≥ 0.95 (该对齐点恰好达线)
        var cacheable = 2001;
        Assert.Equal(1920, PromptCacheKpi.HitCeiling(cacheable));
        Assert.True(PromptCacheKpi.EffectiveHitRate(1920, cacheable) >= PromptCacheRedline.Threshold);
        // 稳健态: 2496 前缀 (39 单元) → 上限 2432 → 0.9744 ≥ 0.95, 且带内最坏点也不越线
        Assert.Equal(2432, PromptCacheKpi.HitCeiling(2496));
        for (var extra = 0; extra < 64; extra++)
        {
            var p2 = 2496 + extra;
            var ceiling2 = PromptCacheKpi.HitCeiling(p2);
            var rate2 = PromptCacheKpi.EffectiveHitRate(ceiling2, p2);
            Assert.False(PromptCacheRedline.Violated(2, p2, rate2),
                $"前缀 {p2} 上限 {ceiling2} → {rate2} 不应越线 (最坏对齐不得掉出 95%)");
        }
    }

    [Fact]
    public void 防漂移_KPI脚本红线阈值必须与代码常量一致()
    {
        // 阈值散落两处 (C# 判定 + python 离线聚合) 极易漂移 → 机检锁死
        var root = AppContext.BaseDirectory;
        var dir = new DirectoryInfo(root);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "scripts", "kpi_cache_hit.py"))) dir = dir.Parent;
        Assert.NotNull(dir);
        var script = File.ReadAllText(Path.Combine(dir!.FullName, "scripts", "kpi_cache_hit.py"));
        Assert.Contains("REDLINE = 0.95", script);
        Assert.DoesNotContain("REDLINE = 0.90", script);
        Assert.Equal(0.95, PromptCacheRedline.Threshold);
    }
}
