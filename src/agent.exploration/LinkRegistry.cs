namespace agent.exploration;

/// <summary>
/// v0.13.3 R276 — 关键文档激活链 (用户钦定思考轮设计稿 §7 → 代码)。
/// 探索发现的 URL 登记入表; 递进未进入时用**三信号预判**重要性 (锚定/结构/递进),
/// 预判分 ≥ 阈值 → 激活 (探索队列高优先级 + 父链 URL 压缩保护)。
/// 不靠召回笼统索引 — 回答用户问题: 递进未进入时凭入链结构信号判关键, 不全保不全丢。
/// </summary>
public sealed class LinkRegistry
{
    private readonly object _lock = new();
    private readonly List<LinkEntry> _links = new();

    /// <summary>激活阈值 (设计稿: 预判分 ≥3 → 激活; 每信号 0-2 分)</summary>
    public const int ActivationThreshold = 3;

    public sealed class LinkEntry
    {
        public string Url { get; set; } = string.Empty;
        /// <summary>发现来源 URL (null = 上下文/任务直接给出)</summary>
        public string? ParentUrl { get; set; }
        public int Depth { get; set; }
        public DateTime DiscoveredAtUtc { get; set; } = DateTime.UtcNow;
        public bool Activated { get; set; }
        public int LastScore { get; set; }
    }

    /// <summary>探索发现 URL 时登记 (ExploreStep.Discovered 挂载点)。</summary>
    public LinkEntry Register(string url, string? parentUrl)
    {
        lock (_lock)
        {
            var existing = _links.FirstOrDefault(l => l.Url == url);
            if (existing != null)
            {
                existing.Depth = Math.Min(existing.Depth, parentUrl == null ? 0 : existing.Depth);
                return existing;
            }
            var entry = new LinkEntry { Url = url, ParentUrl = parentUrl, Depth = parentUrl == null ? 0 : 1 };
            _links.Add(entry);
            return entry;
        }
    }

    /// <summary>
    /// 重要性三信号预判 (设计稿 §7.2.2):
    /// a. 锚定 (0-2): URL/锚文本出现在任务 query (2) 或 ThinkMemory 历史高置信记录 (1);
    /// b. 结构 (0-2): 上层入口页出链数 — 1:1 入口 (2) / 少出链 ≤3 (1);
    /// c. 递进 (0-2): 同探索链连续 2+ 步指向同域同路径前缀 (2) / 同域 (1)。
    /// </summary>
    public int PreJudge(string url, string? taskQuery, IReadOnlyList<string> siblingUrls, bool inThinkMemory)
    {
        var score = 0;

        // a. 锚定信号
        if (!string.IsNullOrEmpty(taskQuery) && taskQuery.Contains(url, StringComparison.OrdinalIgnoreCase))
            score += 2;
        else if (inThinkMemory)
            score += 1;

        // b. 结构信号: 同父出链越少越关键
        var parent = ParentOf(url);
        var siblings = siblingUrls.Count(u => ParentOf(u) == parent);
        if (siblings <= 1) score += 2;
        else if (siblings <= 3) score += 1;

        // c. 递进信号: 同域同路径前缀收敛
        if (siblingUrls.Any(u => u != url && SameDomain(u, url) && PathPrefixOverlap(u, url)))
            score += 2;
        else if (siblingUrls.Any(u => u != url && SameDomain(u, url)))
            score += 1;

        return score;
    }

    /// <summary>激活: ≥ 阈值 → Activated=true, 并标记父链保护 (父 URL 一并返回 — 压缩哨兵保护父链入口)。</summary>
    public IReadOnlyList<string> ActivateIfWorthy(LinkEntry entry, int score, string taskQuery, IReadOnlyList<string> siblingUrls, bool inThinkMemory)
    {
        var protectedUrls = new List<string>();
        lock (_lock)
        {
            entry.LastScore = score;
            if (score >= ActivationThreshold)
            {
                entry.Activated = true;
                protectedUrls.Add(entry.Url);
                // 激活链保护: 父链 (中间入口层) URL 强制保留
                var cur = entry;
                while (!string.IsNullOrEmpty(cur.ParentUrl))
                {
                    var parent = _links.FirstOrDefault(l => l.Url == cur.ParentUrl);
                    if (parent == null)
                    {
                        protectedUrls.Add(cur.ParentUrl);
                        break;
                    }
                    if (!protectedUrls.Contains(parent.Url)) protectedUrls.Add(parent.Url);
                    cur = parent;
                }
            }
        }
        return protectedUrls;
    }

    /// <summary>快照 (打点/测试用)。</summary>
    public IReadOnlyList<LinkEntry> Snapshot()
    {
        lock (_lock) return _links.ToList();
    }

    public int Count { get { lock (_lock) return _links.Count; } }

    private static string? ParentOf(string url)
    {
        var i = url.LastIndexOf('/');
        return i > "https://".Length ? url[..i] : null;
    }

    private static bool SameDomain(string a, string b)
    {
        try
        {
            return new Uri(a).Host == new Uri(b).Host;
        }
        catch
        {
            return false;
        }
    }

    private static bool PathPrefixOverlap(string a, string b)
    {
        try
        {
            var pa = new Uri(a).AbsolutePath.Split('/', StringSplitOptions.RemoveEmptyEntries);
            var pb = new Uri(b).AbsolutePath.Split('/', StringSplitOptions.RemoveEmptyEntries);
            // 目录段 (去末段文件名) 前缀比较 — critical-doc-42 vs critical-doc-43 共享 /internal/ 目录
            var da = pa.Length > 1 ? pa[..^1] : pa;
            var db = pb.Length > 1 ? pb[..^1] : pb;
            var n = Math.Min(da.Length, db.Length);
            return n > 0 && da[..n].SequenceEqual(db[..n]);
        }
        catch
        {
            return false;
        }
    }
}
