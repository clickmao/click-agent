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
        // R352-b (用户钦定): 原文 embed 与压缩主干并行 — embed 不依赖压缩产物, 串行纯白等一次 embed 延迟。
        // Core 收 originalEmbedding=null (内部语义校验跳过), 校验在外层 embed 就绪后补做 (行为等价)。
        var embedTask = _embedder.EmbedAsync(request.Content, ct);
        var coreTask = CompressCoreAsync(request, null, ct);
        await Task.WhenAll(embedTask, coreTask).ConfigureAwait(false);
        var originalEmbedding = embedTask.Result;
        var gr = coreTask.Result;
        // 防漂移第二重 (等价外移): 语义相似度 — 仅 SummarySentences 档 (0.5-0.8) 且产物非全文
        if (gr.Level == GradientLevel.SummarySentences && gr.Content.Length < (request.Content?.Length ?? 0))
        {
            var compressedEmbedding = await _embedder.EmbedAsync(gr.Content, ct).ConfigureAwait(false);
            var cosine = VectorMath.Cosine(originalEmbedding, compressedEmbedding);
            gr.SemanticSimilarity = cosine;
            if (cosine < _semanticThreshold)
            {
                gr.Level = GradientLevel.Full;
                gr.Content = request.Content ?? string.Empty;
                gr.CompressedChars = gr.Content.Length;
            }
        }
        return gr;

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
            // v0.13.3 A3c (audit 实证): 无标点长文本 chunks 多, 固定 4 句装不下关键句 —
            // 配额自适应: 4 句起步, 长文按 chunk 总数放大 (上限 12):
            GradientLevel.SummarySentences => TakeSentences(content, Math.Min(12, Math.Max(4, SplitSentences(content).Count / 8))),
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

                // v0.13.3 D2 (用户问询驱动): 关键信息哨兵 (M3) — 数字串/日期/编号 压缩前提取,
        // 产物缺失任一 → 逐级降级 (当前级别 → RuleCompress → 全文); 补 semantic 盲区
        // (audit 实证: cos 0.996 下数字/指令仍可丢)。
        var sentinels = ExtractSentinels(content);
        var sentinelLosses = new List<string>();
        if (sentinels.Count > 0 && level != GradientLevel.Full)
        {
            var lost = sentinels.Where(sk => !result.Contains(sk, StringComparison.Ordinal)).ToList();
            if (lost.Count > 0)
            {
                // 降级一档: SummarySentences/TitleOnly 丢失 → RuleCompress (保关键句评分语义);
                result = RuleCompress(content, request.TokenBudget);
                lost = sentinels.Where(sk => !result.Contains(sk, StringComparison.Ordinal)).ToList();
                if (lost.Count > 0)
                {
                    level = GradientLevel.Full;
                    result = content; // 终极回退: 宁大不歪
                }
                sentinelLosses = lost;
            }
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
            SentinelLosses = sentinelLosses,
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
        // A3c (audit 85% 实证): 指令句权重上调 — 无标点样本 chunk 摘句竞争中指令句败给因果句;
        // 指令句是多标记叠加 (必须+不得+务必), 单标记 +3 不足以保入选:
        var instrHits = 0;
        foreach (var w in new[] { "必须", "注意", "不得", "禁止", "先经", "应当", "务必" })
            if (s.Contains(w, StringComparison.Ordinal)) instrHits++;
        score += instrHits switch { >= 2 => 7, 1 => 3, _ => 0 };
        var digitCount = s.Count(char.IsDigit);
        if (digitCount >= 4) score += 2;
        else if (digitCount > 0) score += 1;
        if (s.Contains("编号", StringComparison.Ordinal) || s.Contains("SN-", StringComparison.Ordinal)) score += 1;
        return score;
    }


    /// <summary>v0.13.3 D2: 关键信息哨兵提取 — 数字串(≥3位)/日期/SN 编号/引号内实体</summary>
    internal static List<string> ExtractSentinels(string content)
    {
        var sentinels = new List<string>();
        foreach (System.Text.RegularExpressions.Match m in
                 System.Text.RegularExpressions.Regex.Matches(content, @"\d{3,}"))
            if (m.Value.Length >= 3 && !sentinels.Contains(m.Value)) sentinels.Add(m.Value);
        foreach (System.Text.RegularExpressions.Match m in
                 System.Text.RegularExpressions.Regex.Matches(content, @"\d{4}-\d{2}-\d{2}"))
            if (!sentinels.Contains(m.Value)) sentinels.Add(m.Value);
        foreach (System.Text.RegularExpressions.Match m in
                 System.Text.RegularExpressions.Regex.Matches(content, @"SN-\d+"))
            if (!sentinels.Contains(m.Value)) sentinels.Add(m.Value);
        // v0.13.3 R281 (D2 扩展, 设计稿 §7.3): URL 哨兵 — 链接入口是探索/激活链的载体,
        // audit 实证含链接文档 keys 14% (URL 大丢)。截尾标点避免把句末逗号句号计入:
        foreach (System.Text.RegularExpressions.Match m in
                 System.Text.RegularExpressions.Regex.Matches(content, @"https?://[^\s,，。;；)" + "\"" + "'" + "]+"))
        {
            var url = m.Value.TrimEnd('.', ',', ')', '}', ']');
            if (url.Length > 8 && !sentinels.Contains(url)) sentinels.Add(url);
        }
        return sentinels;
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
        // v0.13.3 A3b (audit 多样态实证): 无标点样式整段一句 → 句切分失效, 摘句丢关键句
        // (instruction 85% 根因)。二次切分: 超长段 (≥120ch) 按 maxSentences 粒度均分 chunk,
        // 保证关键句保护在无标点文本上也有操作粒度:
        if (parts.Count == 1 && parts[0].Length >= 120)
        {
            var chunked = new List<string>();
            var chunkSize = Math.Max(80, parts[0].Length / 4);
            var rest = parts[0];
            var keepMarkers = new[] { "必须", "不得", "禁止", "务必", "先经", "签字", "应当" };
            while (rest.Length > chunkSize * 2)
            {
                // 优先在连接词处切 (因为/因此/所以/注意/必须 — 关键句边界):
                var cut = chunkSize;
                foreach (var w in new[] { "因为", "因此", "所以", "注意", "由于" })
                {
                    var idx = rest.IndexOf(w, chunkSize / 2, StringComparison.Ordinal);
                    if (idx > 0) { cut = idx; break; }
                }
                // 防切断关键标记词内部 (A3b 实证: "必须先经过" 被硬切 → Contains 失败):
                foreach (var mk in keepMarkers)
                {
                    var mkIdx = rest.IndexOf(mk, StringComparison.Ordinal);
                    if (mkIdx > 0 && Math.Abs(mkIdx - cut) < mk.Length)
                        cut = mkIdx > cut ? mkIdx : Math.Max(0, mkIdx - 20); // 切点让位到标记词边界外
                }
                chunked.Add(rest[..cut]);
                rest = rest[cut..];
            }
            chunked.Add(rest);
            return chunked.Where(p => !string.IsNullOrWhiteSpace(p)).ToList();
        }
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
