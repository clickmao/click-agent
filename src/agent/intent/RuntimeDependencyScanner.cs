using System;
using System.Collections.Generic;
using System.Linq;

namespace agent.intent;

/// <summary>
/// 运行时依赖识别 (v0.22.0 exp9 D7)。
///
/// 为什么必须确定性: "A 跑到中途要用 B 的产出" 若靠 LLM 判断"这句话是不是在要 B 的数据",
/// 就会出现"该等的没等 / 不该等的瞎等" —— 两种都直接破坏正确性 (前者伪造数据, 后者死等)。
/// 因此只认**显式契约**, 不猜自然语言:
///   ① `$node:&lt;id&gt;` / `$dep:&lt;id&gt;` 占位符 (节点文本或其参数值中出现);
///   ② `&lt;id&gt;的产出|输出|结果|产物` (大小写不敏感; id 必须是**本计划已知节点**且不是自己)。
/// 契约由静态前缀前置注入 (前置知识注入口径) —— 让模型产出可被框架确定性编排的接口, 而不是让框架猜模型。
///
/// 不在契约内的自然语言引用 (如"等它出结果") **一律不认** (诚实边界, 见计划 §12): 宁可不等 (由执行体自己报错),
/// 也不许瞎等/瞎兜底。
/// </summary>
public static class RuntimeDependencyScanner
{
    /// <summary>显式占位符前缀 (静态前缀里前置注入的契约)</summary>
    public static readonly string[] PlaceholderPrefixes = ["$node:", "$dep:"];

    /// <summary>文本引用后缀 (id + 后缀 = "要它的产出")</summary>
    private static readonly string[] TextSuffixes = ["的产出", "的输出", "的结果", "的产物", "产出", "输出"];

    /// <summary>
    /// 找出该节点运行时依赖的生产节点 Id; 无 = null。
    /// 自引用 (指向自己) 视为配置错误 → **不等待**, 返回 null (由执行体自己暴露问题, 不许自等死锁)。
    /// 未知 id (不在本计划) → **不等待**, 返回 null (不许等一个永远不存在的节点)。
    /// </summary>
    public static string? FindProducer(PlanNode node, IReadOnlyList<PlanNode> planNodes)
    {
        var known = planNodes.Where(n => !string.Equals(n.Id, node.Id, StringComparison.Ordinal))
            .Select(n => n.Id).ToHashSet(StringComparer.OrdinalIgnoreCase);

        foreach (var candidate in ScanTexts(node))
        {
            if (string.IsNullOrEmpty(candidate))
                continue;
            if (known.Contains(candidate))
                return planNodes.First(n => string.Equals(n.Id, candidate, StringComparison.OrdinalIgnoreCase)).Id;
        }
        return null;
    }

    /// <summary>按优先级扫描: 节点文本 → 参数值 (参数值也是模型可控输入, 同一条契约)</summary>
    private static IEnumerable<string?> ScanTexts(PlanNode node)
    {
        yield return ScanPlaceholder(node.Text);
        foreach (var p in node.Parameters)
            yield return ScanPlaceholder(p.Value);

        foreach (var other in ScanTextRefs(node))
            yield return other;
    }

    private static IEnumerable<string?> ScanTextRefs(PlanNode node)
    {
        var text = node.Text ?? string.Empty;
        foreach (var suffix in TextSuffixes)
        {
            var idx = 0;
            while (true)
            {
                idx = text.IndexOf(suffix, idx, StringComparison.Ordinal);
                if (idx < 0)
                    break;
                var id = ReadIdBackwards(text, idx);
                if (id.Length > 0)
                    yield return id;
                idx += suffix.Length;
            }
        }
        // 覆盖 "$node:id 的产出" 这类"占位符+中文后缀"混写: 占位符扫描已覆盖前缀形式, 这里不重复。
    }

    /// <summary>从后缀起点向前读一个 id (允许字母/数字/_/-/. 组成), 常见前缀分隔符 (空格/冒号/引号/顿号) 跳过</summary>
    private static string ReadIdBackwards(string text, int endExclusive)
    {
        var end = endExclusive;
        while (end > 0 && IsSeparator(text[end - 1]))
            end--;
        var start = end;
        while (start > 0 && IsIdChar(text[start - 1]))
            start--;
        return start == end ? string.Empty : text[start..end];
    }

    /// <summary>提取 `$node:&lt;id&gt;` / `$dep:&lt;id&gt;` 中的 id (第一个命中即返回)</summary>
    internal static string? ScanPlaceholder(string? text)
    {
        if (string.IsNullOrEmpty(text))
            return null;
        foreach (var prefix in PlaceholderPrefixes)
        {
            var idx = text.IndexOf(prefix, StringComparison.OrdinalIgnoreCase);
            if (idx < 0)
                continue;
            var start = idx + prefix.Length;
            var end = start;
            while (end < text.Length && IsIdChar(text[end]))
                end++;
            if (end > start)
                return text[start..end];
        }
        return null;
    }

    private static bool IsSeparator(char c) => c is ' ' or '\t' or '"' or '\'' or '「' or '『' or ':' or '：' or '、' or ',' or '，' or '(' or '（';

    private static bool IsIdChar(char c) => char.IsLetterOrDigit(c) || c is '_' or '-' or '.';
}
