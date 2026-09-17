using agent.llamacpp;
using agent.modelqueue;
using Xunit;
namespace agent.tests;

/// <summary>
/// R411 J5: llama.cpp 的 prompt 计数字段语义（**独立实现钉死**，见 eval/rover/r411/semantics.json）。
///
/// `/completion` 响应:
///   • <c>tokens_evaluated</c>（顶层）= **本轮 prompt 总长**（含 BOS）—— 不是「新评估数」；
///   • <c>timings.prompt_n</c> = 本轮**新评估**数；<c>timings.cache_n</c> = 命中复用数；
///   • 关系: <c>tokens_evaluated == timings.prompt_n + timings.cache_n</c>。
///
/// 实测（同一渲染串，独立 /tokenize 对账）: 冷 496/497/497/0；热 529/530/18/512。
/// 教训: 「evaluated」字面像新算数，实际是总长 ⇒ **口径必须靠独立实现对账钉死，不能按字段名猜**。
/// </summary>
public sealed class LlamaCppPromptAccountingTests
{
    [Fact]
    public void Total_IsTokensEvaluated_NoAddition()
    {
        // 冷启: 总长 497 = prompt_n 497 + cache_n 0
        Assert.Equal(497, LlamaCppTextGenerator.RecomputedTokens(497, 0));
        // 热轮: 总长 530 = prompt_n 18 + cache_n 512 ⇒ 重算 = 18
        Assert.Equal(18, LlamaCppTextGenerator.RecomputedTokens(530, 512));
    }

    [Fact]
    public void Recomputed_NeverNegative()
    {
        Assert.Equal(0, LlamaCppTextGenerator.RecomputedTokens(530, 530));
        Assert.Equal(530, LlamaCppTextGenerator.RecomputedTokens(530, -1));   // 未上报 ⇒ 全部视作重算
    }

    [Fact]
    public void Trap_OldFormulaHalvesTheRatio()
    {
        // 负控: 若按「总长 = tokens_evaluated + cache_n」算 ⇒ 总长虚增到 1042，
        // 会话整体复用率被腰斩（0.4913 vs 真值 0.9660）—— 指标失真方向是**低估**。
        const int evaluated = 530, cached = 512;
        var wrongTotal = evaluated + cached;                     // 1042（错）
        Assert.Equal(0.4914, Math.Round(cached / (double)wrongTotal, 4));
        Assert.Equal(0.966, Math.Round(cached / (double)evaluated, 4));   // 真值（evaluated 即总长）
        // 独立实现测得的渲染串长度 529 与 evaluated(530) 只差 BOS ⇒ 1042 物理不可能
        Assert.True(Math.Abs(evaluated - 529) <= 1);
    }

    [Fact]
    public void RedlineArithmetic_ShortPrefixCannotPassOnAbsoluteLength()
    {
        Assert.Equal(4224, LocalSessionCacheLedger.RequiredPrefixTokens);
        Assert.Equal(4224, PromptCacheKpi.PrefixTokensNeededFor(PromptCacheRedline.Threshold));
    }
}
