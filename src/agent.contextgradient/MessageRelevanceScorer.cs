namespace agent.contextgradient;

/// <summary>
/// 消息相关性混合打分 (v0.11.0 P3 向量化 — 用户钦定):
/// 词面 (关键词命中率) + 语义 (bge 向量余弦) 混合。embedder 不可用 → 纯词面 (P1 行为兼容)。
/// 静态纯函数: 零实例依赖 (可测性/低耦合), embedder 经参数注入并经 <see cref="TryEmbedQueryAsync"/>
/// 登记到 <see cref="ActiveEmbedder"/> 供消息向量嵌入复用同一实例。
/// </summary>
public static class MessageRelevanceScorer
{
    /// <summary>词面权重 (精确命中可靠, 为主)</summary>
    private const double LexicalWeight = 0.6;

    /// <summary>语义权重 (补同义改写, 为辅)</summary>
    private const double SemanticWeight = 0.4;

    /// <summary>强语义抬底线 (cos ≥ 0.8 直接视为强相关 — 同义改写不因词面缺失被埋没)</summary>
    private const double StrongSemanticFloor = 0.8;

    /// <summary>当前打分使用的嵌入器 (TryEmbedQueryAsync 登记; null = 纯词面模式)。</summary>
    internal static ITextEmbedder? ActiveEmbedder { get; set; }

    /// <summary>
    /// 混合打分 (带 embedder 注入 — 查询向量内部嵌入; 供测试/独立调用)。
    /// </summary>
    public static async Task<double> ScoreWithEmbedderAsync(
        string messageContent, string query, ITextEmbedder? embedder, CancellationToken ct)
    {
        var queryVec = await TryEmbedQueryAsync(embedder, query, ct).ConfigureAwait(false);
        return await ScoreAsync(messageContent, query, queryVec, precomputedKeywords: null, ct).ConfigureAwait(false);
    }

    /// <summary>
    /// 混合打分核心: queryEmbedding = 查询向量缓存 (调用方一次嵌入多消息复用; null = 纯词面)。
    /// 混合式: 0.6×词面 + 0.4×语义, 强语义 (≥0.8) 抬底; 嵌入失败 → 词面兜底 (召回不中断)。
    /// </summary>
    public static async Task<double> ScoreAsync(
        string messageContent, string query, float[]? queryEmbedding,
        List<string>? precomputedKeywords, CancellationToken ct)
    {
        var keywords = precomputedKeywords ?? ExtractKeywords(query);
        var matches = 0;
        foreach (var k in keywords)
        {
            if (messageContent.Contains(k, StringComparison.OrdinalIgnoreCase))
                matches++;
        }
        var lexical = matches > 0 ? (double)matches / Math.Max(1, keywords.Count) : 0.1;

        // 语义分量: 无查询向量 (未嵌入/嵌入失败/不可用) → 纯词面 (P1 兼容)
        if (queryEmbedding is null || queryEmbedding.Length == 0)
            return lexical;

        try
        {
            var embedder = ActiveEmbedder;
            if (embedder is null || !embedder.IsAvailable)
                return lexical;
            var msgVec = await embedder.EmbedAsync(messageContent, ct).ConfigureAwait(false);
            if (msgVec.Length == 0)
                return lexical;
            var semantic = Math.Max(0, VectorMath.Cosine(queryEmbedding, msgVec)); // [-1,1] → [0,1]
            var blended = LexicalWeight * lexical + SemanticWeight * semantic;
            return Math.Max(blended, semantic >= StrongSemanticFloor ? StrongSemanticFloor : 0);
        }
        catch
        {
            return lexical; // 嵌入失败 → 词面兜底 (行为兼容)
        }
    }

    /// <summary>查询向量嵌入 (一轮一次; 不可用/失败 → null, 调用方按纯词面处理, 不重试)。</summary>
    public static async Task<float[]?> TryEmbedQueryAsync(ITextEmbedder? embedder, string query, CancellationToken ct)
    {
        ActiveEmbedder = embedder; // 登记供消息向量嵌入复用 (同一 bge 实例, 不重复加载)
        if (embedder is null || !embedder.IsAvailable)
            return null;
        try
        {
            return await embedder.EmbedAsync(query, ct).ConfigureAwait(false);
        }
        catch
        {
            return null; // 本轮纯词面 (与 TriggerMatcher 失败静默策略一致)
        }
    }

    /// <summary>
    /// 关键词提取: 英文按空格 (≥3 词长) + 中文整段切 2 字滑窗 (宿主 ExtractKeywords 对中文的等效行为 —
    /// 宿主按空格分词对无空格中文整段落入单 token 后 len>2 保留; 此处滑窗更细但命中语义一致)。
    /// </summary>
    private static List<string> ExtractKeywords(string text)
    {
        var kws = new List<string>();
        foreach (var seg in text.Split(' ', StringSplitOptions.RemoveEmptyEntries))
        {
            if (StopWords.Contains(seg))
                continue;
            var isCjk = seg.Length > 0 && seg[0] >= 0x4E00 && seg[0] <= 0x9FFF;
            if (isCjk)
            {
                // 中文: 2 字滑窗 (查询粒度与消息内容匹配)
                for (var i = 0; i + 2 <= seg.Length; i++)
                    kws.Add(seg.Substring(i, 2));
            }
            else if (seg.Length > 2)
            {
                kws.Add(seg);
            }
        }
        return kws.Distinct().Take(10).ToList();
    }

    private static readonly HashSet<string> StopWords = new(StringComparer.OrdinalIgnoreCase)
    {
        "the", "and", "for", "with", "what", "how", "why",
        "这个", "那个", "什么", "怎么", "如何", "一下", "请问",
    };
}
