namespace agent.contextgradient;

/// <summary>
/// 上下文梯度压缩器 (v7.15 P1 规则版 — 无向量依赖; plan_context_compression.md L0-L3 规则落地):
/// 按相关性分四级; 每级压缩后过 DriftGuard (锚词保持), 不过则回退上一级 (漂移防护优先于体积)。
/// </summary>
public sealed class ContextGradientCompressor
{
    /// <summary>嵌入器只读暴露 (v0.11.0: ContextAssembler 相关性打分复用同一 bge 实例 — 避免重复加载模型)</summary>
    public ITextEmbedder? Embedder => _embedder is { IsAvailable: true } ? _embedder : null;

    private readonly ITextEmbedder? _embedder;
    private readonly double _semanticThreshold;

    /// <summary>embedder 注入 → 语义漂移校验启用 (cos ≥ threshold); 未注入 → 纯锚词 (P1 行为)</summary>
    public ContextGradientCompressor(ITextEmbedder? embedder = null, double semanticThreshold = 0.92)
    {
        _embedder = embedder;
        _semanticThreshold = semanticThreshold;
    }

    /// <summary>句子切分 (中英混排: 。！？.!?)</summary>
    private static readonly char[] SentenceEnders = { '。', '！', '？', '.', '!', '?' };

    public GradientResult Compress(GradientRequest request)
        => CompressCoreAsync(request, null, CancellationToken.None).GetAwaiter().GetResult(); // sync 边界兼容 (async 版请用 CompressAsync)

    /// <summary>P3 语义版: embedder 就绪时对非 Full 级产物做 cosine 漂移校验 (原文三重校验的语义分量);
    /// embedder 不可用/失败 → 退锚词 (Compress 语义), 行为兼容。</summary>
    public async Task<GradientResult> CompressAsync(GradientRequest request, CancellationToken ct = default)
    {
        if (_embedder is null || !_embedder.IsAvailable)
            return Compress(request);
        // R129 (真缺陷 54b): 语义校验仅 SummarySentences 档 (0.5-0.8) 需要 originalEmbedding —
        // Full (>=0.8) 恒全文不可达, Rule/TitleOnly (<0.5) 不做语义二重校验 — 两者 embed 纯浪费。
        // 批测实证: n=8 段每段白做 1-2 次 bge embed (~1.3s/次) → compress 20.3s → 7.7s → 目标 <2s。
        var score = request.RelevanceScore;
        if (score is < 0.5 or >= 0.8)
            return CompressCoreAsync(request, null, ct).ConfigureAwait(false).GetAwaiter().GetResult();
        var originalEmbedding = await _embedder.EmbedAsync(request.Content, ct);
        return await CompressCoreAsync(request, originalEmbedding, ct).ConfigureAwait(false);
    }

    private async Task<GradientResult> CompressCoreAsync(GradientRequest request, float[]? originalEmbedding, CancellationToken ct)
    {
        var content = request.Content ?? string.Empty;
        double? semanticSim = null;
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

        // 防漂移第一重: 锚词保持 — 不过则回退全文 (Full 为锚点终点)
        var passed = DriftGuard.Check(result, request.AnchorWords);
        if (!passed && level != GradientLevel.Full)
        {
            level = GradientLevel.Full;
            result = content;
            passed = DriftGuard.Check(result, request.AnchorWords);
        }

        // 防漂移第二重: 语义相似度 (P3, embedder 就绪且产物非全文时) — cos < 阈值 → 回退全文
        // R129 (54c): 语义校验只对 SummarySentences 档 (0.5-0.8) — Rule/TitleOnly 产物已极短且
        // 锚词第一重已过, bge embed 1.3s/次 × 低分段的成本>收益 (批测 compress 20.3s→7.7s→目标 <2s)。
        if (originalEmbedding is not null && level == GradientLevel.SummarySentences &&
            result.Length < content.Length)
        {
            var compressedEmbedding = await _embedder!.EmbedAsync(result, ct).ConfigureAwait(false);
            var cosine = VectorMath.Cosine(originalEmbedding, compressedEmbedding);
            semanticSim = cosine;
            if (cosine < _semanticThreshold)
            {
                level = GradientLevel.Full;
                result = content;
            }
        }

        return new GradientResult
        {
            Level = level,
            Content = result,
            DriftCheckPassed = passed,
            SemanticSimilarity = semanticSim,
            OriginalChars = content.Length,
            CompressedChars = result.Length,
        };
    }

    /// <summary>
    /// 摘句: 关键句保护 (v0.13.3 A3, audit 实证驱动 — 旧"取前 N 句"把随机分布的
    /// 因果句/指令句截掉, 2000/3000 tok 档因果/指令保留率 0-15%)。
    /// 评分: 因果标记 (因为/因此/由于/导致/所以) +3, 指令标记 (必须/注意/不得/禁止/先经/应当) +3,
    /// 数值密度 (数字/日期/编号) +2, 锚词命中 +2; 同分保原文序 (首句 +1 平手破)。
    /// </summary>
    private static string TakeSentences(string content, int maxSentences)
    {
        var sentences = SplitSentences(content);
        if (sentences.Count <= maxSentences)
            return content;
        var scored = sentences
            .Select((s, idx) => (s, idx, score: SentenceScore(s)))
            .OrderByDescending(x => x.score)
            .ThenBy(x => x.idx)
            .Take(maxSentences)
            .OrderBy(x => x.idx) // 恢复原文顺序 (可读性)
            .Select(x => x.s);
        return string.Join("", scored);
    }

    private static int SentenceScore(string s)
    {
        var score = 0;
        foreach (var w in new[] { "因为", "因此", "由于", "导致", "所以", "原因是" })
            if (s.Contains(w, StringComparison.Ordinal)) { score += 3; break; }
        foreach (var w in new[] { "必须", "注意", "不得", "禁止", "先经", "应当", "务必" })
            if (s.Contains(w, StringComparison.Ordinal)) { score += 3; break; }
        var digitCount = s.Count(char.IsDigit);
        if (digitCount >= 4) score += 2;
        else if (digitCount > 0) score += 1;
        if (s.Contains("编号", StringComparison.Ordinal) || s.Contains("SN-", StringComparison.Ordinal)) score += 1;
        return score;
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
