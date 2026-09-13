using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R380 (用户钦定**口径修订**, 首要 KPI) 机检:
/// 命中率**只算"需要命中的部分"** —— 本轮新增不计入 (新增必然不命中, 计入即稀释指标)。
///   有效命中率 = hit / min(本轮 prompt, 上一轮同会话 prompt); 会话首轮不适用 (-1)。
/// 红线: 多轮会话第 2 轮起 ≥**97%** (R380 90→95, R393 用户 OOB 95→97; 目标 98~99%); 越线必须查因并修复。
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
    public void 红线_第2轮起低于97判定越线_首轮与无分母不判定()
    {
        Assert.Equal(0.97, PromptCacheRedline.Threshold);
        Assert.True(PromptCacheRedline.Violated(2, 981, 0.9699));
        Assert.False(PromptCacheRedline.Violated(2, 981, 0.97));
        // 旧 95% 红线下的"达标"值 (0.95~0.97) 在新红线下必须判越线 —— 提高红线的判别力证明
        Assert.True(PromptCacheRedline.Violated(2, 981, 0.95));
        Assert.True(PromptCacheRedline.Violated(2, 981, 0.9595));
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
        // 诊断文案必须与新红线同源 (半改红线会出现"判定用 97%、诊断写 95%"的静默分叉)
        Assert.Contains("需前缀 ≥ 4224 token", d);
        Assert.Contains("97%", d);
        Assert.DoesNotContain("95%", d);
    }

    [Fact]
    public void 负向控制_旧口径会把达标轮误判为越线()
    {
        // 真机 mt_fix4 轮 2: 旧口径 0.6608 (含本轮新增 375 token) → 会误判"灾难性失败";
        // 新口径 0.9134 = 该前缀的**理论上限**。断言两者方向相反, 证明口径修正是判定成立的前提。
        // (注: 0.9134 在 97% 红线下仍越线 —— 但归因是**前缀长度不足**, 不是口径问题; 见 达标态 用例)
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
    public void 真机基线_97红线_当前越线且命中恰为理论上限()
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
            // ② 以 97% 红线判定: 前缀严重不足 (上限本身 < 阈值) → 越线 (诚实当前状态, 非回归)
            Assert.True(PromptCacheKpi.HitCeiling(cacheable) < cacheable * PromptCacheRedline.Threshold,
                $"前缀 {cacheable} 的**理论上限** {PromptCacheKpi.HitCeiling(cacheable)} 就低于 97% 红线 → 结构修复无解, 必须加厚前缀");
            Assert.True(PromptCacheRedline.Violated(turn, cacheable, rate),
                $"前缀 {cacheable} 的上限 {PromptCacheKpi.HitCeiling(cacheable)} 不足以达 97% → 应判越线");
            turn++;
        }
    }

    [Fact]
    public void 达标态_前缀达到所需量级则97红线可通过()
    {
        // 算术 (最坏对齐稳健界): **97% ⇒ 前缀 ≥ 4224 token (66 单元)**; 95% ⇒ ≥2496; 98% ⇒ ≥6336; 90% ⇒ ≥1216
        Assert.Equal(4224, PromptCacheKpi.PrefixTokensNeededFor(0.97));
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
        foreach (var t in new[] { 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.97, 0.98, 0.99 })
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
        // 真机 mt_fix5: 前缀 2001 → 上限 1920 → 0.9595。**95% 下达标, 97% 下越线** ——
        // 这条"提高红线后由达标翻转为越线"的实测证据必须留在机检里 (不能只留在报告里)。
        Assert.Equal(1920, PromptCacheKpi.HitCeiling(2001));
        Assert.True(PromptCacheKpi.EffectiveHitRate(1920, 2001) >= 0.95);
        Assert.True(PromptCacheRedline.Violated(2, 2001, PromptCacheKpi.EffectiveHitRate(1920, 2001)),
            "前缀 2001 (上限 1920 = 95.95%) 在 97% 红线下必须判越线");
        Assert.True(PromptCacheKpi.HitCeiling(2001) < 2001 * PromptCacheRedline.Threshold,
            "2001 token 的**理论上限**就低于 97% ⇒ 该前缀下任何结构修复都不可能达标, 只能加厚前缀");
        // 新达标态 (97%): 4224 前缀 (66 单元) → 上限 4160 → 0.9848 ≥ 0.97, 且带内最坏点也不越线
        var need97 = PromptCacheKpi.PrefixTokensNeededFor(PromptCacheRedline.Threshold);
        Assert.Equal(4224, need97);
        Assert.Equal(4160, PromptCacheKpi.HitCeiling(need97));
        Assert.False(PromptCacheRedline.Violated(2, need97, PromptCacheKpi.EffectiveHitRate(4160, need97)));
        for (var extra = 0; extra < 64; extra++)
        {
            var p2 = need97 + extra;
            var ceiling2 = PromptCacheKpi.HitCeiling(p2);
            var rate2 = PromptCacheKpi.EffectiveHitRate(ceiling2, p2);
            Assert.False(PromptCacheRedline.Violated(2, p2, rate2),
                $"前缀 {p2} 上限 {ceiling2} → {rate2} 不应越线 (最坏对齐不得掉出 97%)");
        }
        // 边界负控 (按稳健界的**带**语义, 不是按单元边界): 稳健界前一个 token = 4223 落在 65 单元带
        // [4160, 4224) 的**最坏对齐点** → 上限仍是 4096 → 4096/4223 = 0.9699 < 0.97 必越线。
        // (注: 4160 本身是单元边界, 属该带**最优**对齐 4096/4160 = 0.9846, 拿它做负控是假负控。)
        Assert.Equal(4223, 4224 - 1);
        Assert.Equal(4096, PromptCacheKpi.HitCeiling(4223));
        Assert.True(PromptCacheRedline.Violated(2, 4223, PromptCacheKpi.EffectiveHitRate(4096, 4223)),
            $"前缀 4223 上限 4096 → {PromptCacheKpi.EffectiveHitRate(4096, 4223):P4} 应越线 ⇒ 稳健界 4224 有判别力");
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
        Assert.Contains("REDLINE = 0.97", script);
        Assert.DoesNotContain("REDLINE = 0.90", script);
        Assert.DoesNotContain("REDLINE = 0.95", script);
        Assert.Equal(0.97, PromptCacheRedline.Threshold);
    }
}
