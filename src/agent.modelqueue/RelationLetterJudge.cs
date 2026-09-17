using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;


/// <summary>
/// R426: 本地关系判官输出规范化 (纯函数, 可机检 — 不依赖端口/网络)。
///
/// 纪律与 <see cref="TurnGateJudge.Parse"/> 同源 (R413 实测铁律): **绝不在思考链正文里找标记**
/// (那等于把增益建在噪声上)。只认「思考块闭合之后」的结论区:
/// <list type="bullet">
/// <item>有开无闭 (被 max_tokens 截断) ⇒ 未判定 ⇒ 调用方**远端兜底**;</item>
/// <item>结论区无独立字母 ⇒ 未判定 ⇒ 远端兜底 (绝不猜成 Neutral — 「没测到」≠「判过」);</item>
/// <item>多个独立字母 ⇒ 取**最后**一个 (结论写在推理之后)。</item>
/// </list>
/// </summary>
public static class RelationLetterJudge
{
    /// <summary>
    /// R435: 结论区候选词表 —— **空**（有意）。
    /// 曾经加过「纠正/否定/认可/采纳/新话题/无关 ⇒ 词表定字母」的兜底，被**既有预注册判据 J13** 否决:
    /// `RelationJudgeLocalizationTests.J13` 明文要求「这是采纳」这类**散文必须未判定（交远端）**。
    /// 且四臂实测（A1/A2/A3 vs A0）词表**零增益**（old≡new 逐例相同）⇒ 按「打分不升即回退」撤回。
    /// 结论：判官契约 = 结论区必须有**独立字母**；散文兜底属门（<see cref="TurnGateJudge"/>）的语义，不搬到这里。
    /// </summary>
    private static readonly (string Word, char Letter)[] ConclusionWords =
        System.Array.Empty<(string Word, char Letter)>();

    /// <summary>无思考块闭合标记时，只看结论区尾部这么多字符（镜像 Parse: 防在推理正文里找标记）。</summary>
    private const int ConclusionTailChars = 64;

    /// <summary>规范化: 成功 → <c>true</c> 且 <paramref name="letter"/> ∈ {C,A,N}。</summary>
    public static bool TryNormalize(string? raw, out string letter)
        => TryNormalize(raw, out letter, out _);

    /// <summary>
    /// R435: 带**失败原因**的重载 —— 归因可观测（R434 的缺口：本地原始输出不入遥测,
    /// 遥测里 `letter` 在 fallback 分支被远端文本覆盖 ⇒ 12 条里看不出失败原因）。
    /// 原因枚举（机检可断言）: <c>empty</c> / <c>thinking_truncated</c> / <c>empty_conclusion</c> / <c>no_marker</c> / <c>ok</c>。
    /// </summary>
    public static bool TryNormalize(string? raw, out string letter, out string reason)
    {
        letter = string.Empty;
        reason = "empty";
        if (string.IsNullOrWhiteSpace(raw)) return false;
        var text = raw.Trim();

        var close = text.LastIndexOf(TurnGateJudge.ThinkClose, StringComparison.Ordinal);
        if (close >= 0)
        {
            text = text[(close + TurnGateJudge.ThinkClose.Length)..];
        }
        else if (text.LastIndexOf(TurnGateJudge.ThinkOpen, StringComparison.Ordinal) >= 0)
        {
            reason = "thinking_truncated";   // 有开无闭: 结论还没写出来 (R435: 预算不足的确定形态)
            return false;
        }
        else if (text.Length > ConclusionTailChars)
        {
            // R435: 无思考块 ⇒ 只看尾部 (与 Parse 同规则; 原实现对全文取「最后一个字母」= 允许从推理正文取字母)
            text = text[^ConclusionTailChars..];
        }

        text = text.Trim();
        if (text.Length == 0) { reason = "empty_conclusion"; return false; }

        var last = -1;
        var pick = '\0';
        foreach (System.Text.RegularExpressions.Match m in
                 System.Text.RegularExpressions.Regex.Matches(text, @"(?<![A-Za-z])([CcAaNn])(?![A-Za-z])"))
        {
            last = m.Index;
            pick = char.ToUpperInvariant(m.Groups[1].Value[0]);
        }
        foreach (var (word, letterChar) in ConclusionWords)
        {
            var k = text.LastIndexOf(word, StringComparison.Ordinal);
            if (k > last) { last = k; pick = letterChar; }
        }
        if (last < 0) { reason = "no_marker"; return false; }
        letter = pick.ToString();
        reason = "ok";
        return true;
    }
}
