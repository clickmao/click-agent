using System.Text;

namespace agent.critique;

/// <summary>
/// v0.14.0 T2c (CriticPipeline): 自审结果锚定装配器 — 三级过滤 (plan v0.14.0-master-plan §2.2)。
/// 输入: OutputCritic 静态命中 + SelfCritic LLM 候选 + FixMemory 现有修法。
/// 输出: 确认态条目 (入 FixMemory) / 观察态条目 (仅打点) / 回复尾追加文案。
/// 规则: LLM 单源 = 观察态 (绝不直接进生成上下文); 双源独立同判 = 强锚。
/// </summary>
public static class CriticPipeline
{
    public sealed record AnchoredFinding(
        string Pattern, string Mechanism, string FixHint, bool Confirmed, string Evidence);

    /// <summary>
    /// 装配: 静态命中 (强锚) ∪ LLM 候选 (逐字锚已在 SelfCritic.Parse 完成, 此处查重 FixMemory 与静态交叉)。
    /// quote 逻辑: LLM 候选 quote 与静态命中 snippet 有包含关系 → 视为同一问题双源确认。
    /// </summary>
    public static (IReadOnlyList<AnchoredFinding> Confirmed, IReadOnlyList<AnchoredFinding> Observed)
        Assemble(
            IReadOnlyList<OutputCritic.Finding> staticFindings,
            IReadOnlyList<SelfCritic.CandidateCritique> llmCandidates,
            FixMemory memory,
            string output)
    {
        var confirmed = new List<AnchoredFinding>();
        var observed = new List<AnchoredFinding>();
        var claimed = new HashSet<string>(); // 已被静态占用的 quote 片段 (防重复计数)

        // 1. 静态命中 = 强锚 (确定性规则, 直接确认态; FixMemory 合并 confirmations++)
        foreach (var f in staticFindings)
        {
            var pattern = f.Snippet;
            var fix = f.Advice;
            var known = memory?.Recall(pattern, 1);
            if (known is { Count: > 0 })
                fix = known[0].Fix; // 已有修法优先 (来源秩在 FixMemory.Write 内维护)
            confirmed.Add(new AnchoredFinding(pattern, $"静态规则 {f.RuleId}: {f.Advice}", fix,
                Confirmed: true, Evidence: $"static:{f.RuleId}"));
            claimed.Add(pattern);
            memory?.Write(pattern, f.Advice, fix, "metric_delta");
        }

        // 2. LLM 候选: 双源 (与静态交叉) → 确认; 单源 → 观察态
        foreach (var c in llmCandidates)
        {
            var cross = staticFindings.Any(sf =>
                c.Quote.Contains(sf.Snippet[..Math.Min(40, sf.Snippet.Length)], StringComparison.Ordinal) ||
                sf.Snippet.Contains(c.Quote[..Math.Min(40, c.Quote.Length)], StringComparison.Ordinal));
            if (cross)
            {
                // 双源同判 — 已在上面静态条目确认过, 跳过 (去重)
                continue;
            }
            var known = memory?.Recall(c.Quote, 1);
            if (known is { Count: > 0 })
            {
                // 修法库已有同 pattern — LLM 独立复判 = 第 2 次确认
                confirmed.Add(new AnchoredFinding(c.Quote, c.Mechanism, known[0].Fix,
                    Confirmed: true, Evidence: "llm+memory"));
                memory?.Write(known[0].Pattern, c.Mechanism, known[0].Fix, "llm_self_confirmed");
            }
            else
            {
                // LLM 单源无锚 — 观察态 (打点可见, 不入生成上下文, 不入修法库)
                observed.Add(new AnchoredFinding(c.Quote, c.Mechanism, c.FixHint,
                    Confirmed: false, Evidence: "llm_only"));
            }
        }
        return (confirmed, observed);
    }

    /// <summary>渲染确认态追加文案 (L1 同点位; 观察态不渲染 — 不打扰用户)。</summary>
    public static string Render(IReadOnlyList<AnchoredFinding> confirmed, int max = 3)
    {
        if (confirmed.Count == 0)
            return string.Empty;
        var sb = new StringBuilder("\n\n> ⚠ 自审: ");
        foreach (var f in confirmed.Take(max))
            sb.Append($"『{f.Pattern}』{f.Mechanism} — 建议: {f.FixHint}; ");
        if (confirmed.Count > max)
            sb.Append($"…另 {confirmed.Count - max} 处。");
        return sb.ToString();
    }

    /// <summary>汇总打点 kv (self_critic 生命周期观测)。</summary>
    public static IEnumerable<(string K, object V)> Telemetry(
        int staticCount, int llmRaw, int llmValid, int confirmed, int observed) =>
        new (string, object)[]
        {
            ("static_hits", staticCount),
            ("llm_raw", llmRaw),
            ("llm_valid", llmValid),
            ("confirmed", confirmed),
            ("observed", observed),
        };
}
