namespace agent.contextgradient;

/// <summary>
/// 上下文梯度压缩器 (v7.15 P1 规则版 — 无向量依赖; plan_context_compression.md L0-L3 规则落地):
/// 按相关性分四级; 每级压缩后过 DriftGuard (锚词保持), 不过则回退上一级 (漂移防护优先于体积)。
/// </summary>
public sealed class ContextGradientCompressor
{
    /// <summary>句子切分 (中英混排: 。！？.!?)</summary>
    private static readonly char[] SentenceEnders = { '。', '！', '？', '.', '!', '?' };

    public GradientResult Compress(GradientRequest request)
    {
        var content = request.Content ?? string.Empty;
        var score = request.RelevanceScore;

        // 层级选择
        var level = score >= 0.8 ? GradientLevel.Full
            : score >= 0.5 ? GradientLevel.SummarySentences
            : score >= 0.3 ? GradientLevel.RuleCompressed
            : GradientLevel.TitleOnly;

        string result = level switch
        {
            GradientLevel.Full => content,
            GradientLevel.SummarySentences => TakeSentences(content, 4),
            GradientLevel.RuleCompressed => RuleCompress(content, request.TokenBudget),
            GradientLevel.TitleOnly => TitleOnly(content),
            _ => content,
        };

        // 防漂移: 锚词保持校验 — 不过则回退上一级 (Full 为锚点终点)
        var passed = DriftGuard.Check(result, request.AnchorWords);
        if (!passed && level != GradientLevel.Full)
        {
            level = GradientLevel.Full;
            result = content;
            passed = true; // 全文必含锚词 (锚词来自原文的话); 若原文本身缺锚, 如实报未过
            passed = DriftGuard.Check(result, request.AnchorWords);
        }

        return new GradientResult
        {
            Level = level,
            Content = result,
            DriftCheckPassed = passed,
            OriginalChars = content.Length,
            CompressedChars = result.Length,
        };
    }

    /// <summary>摘句: 取前 N 句 (保持原文顺序 — 首句通常最重要)</summary>
    private static string TakeSentences(string content, int maxSentences)
    {
        var sentences = SplitSentences(content);
        if (sentences.Count <= maxSentences)
            return content;
        return string.Join("", sentences.Take(maxSentences));
    }

    private static List<string> SplitSentences(string content)
    {
        var parts = new List<string>();
        var start = 0;
        for (var i = 0; i < content.Length; i++)
        {
            if (Array.IndexOf(SentenceEnders, content[i]) >= 0)
            {
                var len = i - start + 1;
                if (len > 0)
                    parts.Add(content.Substring(start, len));
                start = i + 1;
            }
        }
        if (start < content.Length)
            parts.Add(content[start..]);
        return parts.Where(p => !string.IsNullOrWhiteSpace(p)).ToList();
    }

    /// <summary>L2 规则压缩: 去空行/去重复行/按预算截断 (整行截断不切词)</summary>
    private static string RuleCompress(string content, int tokenBudget)
    {
        var lines = content.Split('\n')
            .Select(l => l.TrimEnd())
            .Where(l => l.Trim().Length > 0)
            .Distinct(StringComparer.Ordinal)  // 重复行去重 (规则级)
            .ToList();
        var sb = new System.Text.StringBuilder();
        var budgetChars = Math.Max(64, tokenBudget * 2); // 粗算: 1 token ≈ 2 chars (中英混合)
        foreach (var line in lines)
        {
            if (sb.Length + line.Length + 1 > budgetChars && sb.Length > 0)
                break;
            sb.Append(line + "\n");
        }
        return sb.ToString().TrimEnd();
    }

    /// <summary>L3: 仅首行/标题 (≤80 字符)</summary>
    private static string TitleOnly(string content)
    {
        var first = content.Split('\n').FirstOrDefault(l => l.Trim().Length > 0) ?? string.Empty;
        return first.Length <= 80 ? first : first[..80] + "…";
    }
}

/// <summary>
/// 防漂移校验 (三重规则的 P1 简化 — 锚词保持):
/// 压缩产物必须保留 ≥1 锚词 (锚词为空 = 无锚需求, 恒过)。
/// </summary>
public static class DriftGuard
{
    public static bool Check(string compressed, List<string> anchorWords)
    {
        if (anchorWords.Count == 0)
            return true;
        return anchorWords.Any(w =>
            w.Length > 0 && compressed.Contains(w, StringComparison.OrdinalIgnoreCase));
    }
}
