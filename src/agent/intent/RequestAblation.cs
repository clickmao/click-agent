using System.Text;
using System.Linq;

namespace agent.intent;

/// <summary>
/// 出站文本扣减 (v0.22.0 exp9 D4b)。
///
/// 为什么必须有这一步 —— "位置路由"的语义闭环:
///   路由判定一个子请求是 <see cref="NodeExecutionLocation.Local"/>, 意思是**框架自己把它做完**。
///   若该子请求仍原样随出站文本发给模型, 模型必然再算一遍 ⇒ 同一件事算两次:
///   真机实测 (R382): 框架确定性统计 = 117 字符, 模型自己算出来 = 118 字符 —— 不但白花 token,
///   而且**用户看到的是模型那个错的数**。所以: 判 Local ⇒ 必须从出站文本里扣掉, 结论由框架自渲染
///   (<see cref="PlanLocalAnswer"/>)。
///
/// 硬约束 (全部是"宁可不扣"的保守方向, 逐条可单测):
///   ① 片段必须在原文中**唯一**出现 (0 次 = 定位失败; ≥2 次 = 无法确定删哪处) → 不扣
///   ② 相邻/重叠的片段**合并**为一段删除 (合并区间只含"片段 + 连接词/边界字符", 无用户别的诉求)
///   ③ 扣减后正文占比不得低于 <see cref="MinRemainRatio"/> (整段请求都被本地包住 ⇒ 那是"本地独占回合",
///      见 exp9 §10 边界: 本轮不实现, 不许以"扣成空"退化实现) → 不扣
///   ④ 只按**段落边界**扩展删除区间 (边界字符 + 左邻连接词), 不做任何正文改写/空白归一
///      (用户原文可能含代码块, 空白与缩进是语义的一部分)
/// </summary>
public static class RequestAblation
{
    /// <summary>扣减后剩余正文的最小占比 (低于此值 = 整段请求都被本地子请求占满 ⇒ 不扣, 交模型)</summary>
    internal const double MinRemainRatio = 0.25;

    /// <summary>
    /// 计划级入口 (主链唯一调用点, 纯函数便于单测):
    ///   ① 无本地子请求 → 不扣
    ///   ② **全部节点都是本地** ⇒ 那是"本地独占回合"(单轮零 LLM 调用), 本轮不实现, 一律不扣, 交原链路
    ///      (不许用"把原文扣成空"来假装实现)
    ///   ③ 否则进入逐片段扣减 (硬约束见 <see cref="Subtract"/>)
    /// </summary>
    public static AblationResult SubtractForPlan(string sourceText, IReadOnlyList<PlanNode> nodes)
    {
        var clauses = nodes.Where(n => n.IsLocalizedRequest).Select(n => n.Text).ToList();
        if (clauses.Count == 0)
            return AblationResult.NotApplied(sourceText ?? string.Empty, "无本地子请求");
        if (!nodes.Any(n => n.Location != NodeExecutionLocation.Local))
            return AblationResult.NotApplied(sourceText ?? string.Empty,
                "全部节点均为本地 ⇒ 本地独占回合 (§10 边界, 本轮不实现)", clauses);
        return Subtract(sourceText ?? string.Empty, clauses);
    }

    /// <summary>
    /// 从出站原文中扣掉已判本地执行的子请求片段。
    /// </summary>
    /// <param name="sourceText">本轮用户原文 (message.Content, 未改动的原样)</param>
    /// <param name="localizedClauses">已判 Local 的"纯原文级文本处理"子请求片段 (来自 PlanNode.IsLocalizedRequest)</param>
    public static AblationResult Subtract(string sourceText, IReadOnlyList<string> localizedClauses)
    {
        if (string.IsNullOrEmpty(sourceText) || localizedClauses is null || localizedClauses.Count == 0)
            return AblationResult.NotApplied(sourceText ?? string.Empty, "无本地子请求可扣减", localizedClauses);

        var spans = new List<(int Start, int Length)>(localizedClauses.Count);
        foreach (var raw in localizedClauses)
        {
            var clause = raw?.Trim();
            if (string.IsNullOrEmpty(clause))
                continue;

            var first = sourceText.IndexOf(clause, StringComparison.Ordinal);
            if (first < 0)
                return AblationResult.NotApplied(sourceText, $"片段在原文中定位失败: {Head(clause)}", localizedClauses);
            if (sourceText.IndexOf(clause, first + 1, StringComparison.Ordinal) >= 0)
                return AblationResult.NotApplied(sourceText, $"片段在原文中出现多次, 无法确定删哪处: {Head(clause)}", localizedClauses);

            var start = AbsorbLeft(sourceText, first);
            var end = AbsorbRight(sourceText, first + clause.Length);
            spans.Add((start, end - start));
        }

        if (spans.Count == 0)
            return AblationResult.NotApplied(sourceText, "片段全为空", localizedClauses);

        spans.Sort(static (a, b) => a.Start.CompareTo(b.Start));

        // 相邻/重叠区间**合并**成一段再删。
        // 为什么合并而不是放弃: 区间内容只可能是"本地子请求片段 + 连接词/边界字符 + 另一个本地子请求片段"
        // (扩展规则本身只吃这三类字符), 二者之间没有非本地区域 —— 合并既保守又不会误删用户别的诉求。
        var merged = new List<(int Start, int Length)>(spans.Count);
        foreach (var s in spans)
        {
            if (merged.Count > 0)
            {
                var last = merged[^1];
                if (s.Start <= last.Start + last.Length)
                {
                    merged[^1] = (last.Start, Math.Max(last.Start + last.Length, s.Start + s.Length) - last.Start);
                    continue;
                }
            }
            merged.Add(s);
        }

        var removed = merged.Sum(static s => s.Length);
        var remain = sourceText.Length - removed;
        if (remain <= 0 || remain < sourceText.Length * MinRemainRatio)
            return AblationResult.NotApplied(sourceText,
                $"扣减后剩余正文不足 (剩 {remain}/{sourceText.Length} 字符) ⇒ 疑似本地独占回合 (见 §10 边界), 不扣", localizedClauses);

        var sb = new StringBuilder(sourceText);
        for (var i = merged.Count - 1; i >= 0; i--)
            sb.Remove(merged[i].Start, merged[i].Length);

        var ablated = sb.ToString();
        if (ablated.Trim().Length == 0)
            return AblationResult.NotApplied(sourceText, "扣减后正文为空", localizedClauses);

        return new AblationResult(true, ablated, removed, localizedClauses, null);
    }

    /// <summary>
    /// 向左扩展删除区间: 吃掉紧邻的边界字符与被删片段的**连接词** (如 "…计分; 并且统计…" → 连 "并" 与 "; " 一起删,
    /// 不留孤立的 "并且")。连接词只在**词首是边界/串首**时才吃, 防 "sandwich" 里的 "and" 被误吞。
    /// </summary>
    private static int AbsorbLeft(string text, int start)
    {
        var pos = start;
        while (true)
        {
            var moved = false;
            while (pos > 0 && IsBoundary(text[pos - 1]))
            {
                pos--;
                moved = true;
            }

            foreach (var token in IntentDecomposer.AllConnectorTokens)
            {
                if (token.Length == 0 || token.Length > pos)
                    continue;
                var at = pos - token.Length;
                if (string.CompareOrdinal(text, at, token, 0, token.Length) != 0)
                    continue;
                if (at > 0 && !IsBoundary(text[at - 1]))
                    continue;   // 连接词必须自身处于词首 (防 "sandwich"/"sand")
                pos = at;
                moved = true;
                break;
            }

            if (!moved)
                return pos;
        }
    }

    /// <summary>向右只吃边界字符 (后面的连接词属于**下一个**子句, 不许越界吞)</summary>
    private static int AbsorbRight(string text, int end)
    {
        var pos = end;
        while (pos < text.Length && IsBoundary(text[pos]))
            pos++;
        return pos;
    }

    private static bool IsBoundary(char c) => Array.IndexOf(IntentDecomposer.ClauseBoundaryChars, c) >= 0;

    private static string Head(string s) => s.Length <= 40 ? s : s[..40] + "…";
}
