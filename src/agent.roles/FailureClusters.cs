using System.Text.Json;

namespace agent.roles;

/// <summary>
/// R364 (用户钦定方案): 推理中止→失败簇 — 自体失败信号进赏罚账本。
/// 三件:
///   ① 中止检测: LLM 调用超时/token 超限/自证循环 (连续轮回复 embedding 相似度 >0.95 = 原地打转)
///   ② 失败簇归类: 中止时对问题文本提取指纹 (归一化关键词 hash — 离线零成本), 记入簇
///   ③ 前置注入: 新问题指纹命中簇 → 簇罚分达阈值 → prompt 注入先验警告 (求澄清/降级/坦白)
/// 数据模型: failureClusters.json (紧凑 JSON, 手写 Utf8JsonWriter 读写 — AOT 零反射)。
/// </summary>
public sealed class FailureClusters
{
    private const int StagnationWindow = 3;        // 自证循环窗口
    private const double StagnationSimilarity = 0.95;
    private const int PenaltyThreshold = 3;        // 簇罚分 ≥3 → 前置警告

    private readonly object _lock = new();
    private readonly string _storePath;
    private readonly Dictionary<string, (int Timeout, int Stagnation, int Limit)> _clusters = new(StringComparer.OrdinalIgnoreCase);

    public FailureClusters(string storeDir = "data/roles")
    {
        Directory.CreateDirectory(storeDir);
        _storePath = Path.Combine(storeDir, "failureClusters.json");
        Load();
    }

    /// <summary>① 中止判定: 超时/超限直接判; 停滞需看窗口内回复相似度。</summary>
    public static bool IsStagnant(IReadOnlyList<string> recentReplies)
    {
        if (recentReplies.Count < StagnationWindow) return false;
        // 归一化字符 trigram Jaccard 近似 (零嵌入依赖; 同义反复的回复 trigram 高度重合)
        var last = Trigrams(recentReplies[^1]);
        var lastSet = new HashSet<string>(last);
        for (var i = recentReplies.Count - 2; i >= recentReplies.Count - StagnationWindow; i--)
        {
            var prevSet = new HashSet<string>(Trigrams(recentReplies[i]));
            // 双向 Jaccard (|last ∩ prev| / |last ∪ prev|) — 短回复的 trigram 采样稀疏, 用集合比值对长度差异不敏感
            var inter = lastSet.Count(prevSet.Contains);
            var union = lastSet.Count + prevSet.Count - inter;
            if (union == 0 || (double)inter / union < StagnationSimilarity) return false;
        }
        return true;
    }

    /// <summary>② 记中止: kind=timeout|stagnation|limit; question 归类到簇 (指纹)。</summary>
    public void RecordAbort(string kind, string question)
    {
        var key = ClusterKey(question);
        lock (_lock)
        {
            var cur = _clusters.GetValueOrDefault(key);
            _clusters[key] = kind switch
            {
                "timeout" => (cur.Timeout + 1, cur.Stagnation, cur.Limit),
                "stagnation" => (cur.Timeout, cur.Stagnation + 1, cur.Limit),
                _ => (cur.Timeout, cur.Stagnation, cur.Limit + 1),
            };
        }
        Save();
    }

    /// <summary>③ 前置注入: 簇总罚分 ≥阈值 → 警告块 (≤200 chars); 否则空。</summary>
    public string RenderWarning(string question)
    {
        var key = ClusterKey(question);
        int total;
        lock (_lock) total = _clusters.TryGetValue(key, out var c) ? c.Timeout + c.Stagnation + c.Limit : 0;
        if (total < PenaltyThreshold) return string.Empty;
        return $"【自体经验】此主题历史推理中止 {total} 次 (超时/循环/超限)。策略优先级: 先澄清问题边界 → " +
               "给出可执行的降级方案 → 诚实说明做不到的部分。避免长链推理空转。";
    }

    /// <summary>问题指纹: 归一化 + 关键字排序 hash (停用词去除; 中文按字, 英文按词)。</summary>
    internal static string ClusterKey(string question)
    {
        var stop = new HashSet<string> { "的", "了", "吗", "呢", "怎么", "如何", "什么", "请", "帮我", "the", "a", "is", "how", "to" };
        var chars = new List<string>();
        foreach (var raw in question.ToLowerInvariant().Split(' ', StringSplitOptions.RemoveEmptyEntries))
            if (!stop.Contains(raw)) chars.Add(raw);
        foreach (var ch in question)
            if (ch >= 0x4E00 && ch <= 0x9FFF && !stop.Contains(ch.ToString()))
                chars.Add(ch.ToString());
        // 序数排序 (R365 审查): List<string>.Sort() 默认走文化相关比较 — 同一问题在不同 locale
        // 下可能得到不同指纹 (簇归类跨机漂移)。指纹必须文化无关 → StringComparer.Ordinal。
        chars.Sort(StringComparer.Ordinal);
        var joined = string.Join("", chars);
        return joined.Length == 0 ? "EMPTY" : StableHash(joined[..Math.Min(24, joined.Length)]).ToString("X8");
    }

    /// <summary>
    /// 进程间稳定 hash (FNV-1a 32bit)。
    /// 修 (R365 审查): 原用 string.GetHashCode() — .NET Core 对 string 默认**每进程随机化种子**,
    /// 落盘的簇键重启后无法复现 → "跨会话簇归类" 静默失效 (同进程内测试测不出)。
    /// </summary>
    private static uint StableHash(string s)
    {
        var h = 2166136261u;
        foreach (var c in s)
        {
            h ^= c;
            h *= 16777619u;
        }
        return h;
    }

    private static string[] Trigrams(string s)
    {
        s = s.Trim();
        if (s.Length < 3) return new[] { s };
        var list = new List<string>();
        for (var i = 0; i <= s.Length - 3; i++) list.Add(s[i..(i + 3)]);
        return list.ToArray();
    }

    // ── 落盘 ──
    private void Save()
    {
        lock (_lock)
        {
            using var fs = File.Create(_storePath);
            using var w = new Utf8JsonWriter(fs);
            w.WriteStartObject();
            foreach (var (k, c) in _clusters)
            {
                w.WriteStartObject(k);
                w.WriteNumber("t", c.Timeout);
                w.WriteNumber("s", c.Stagnation);
                w.WriteNumber("l", c.Limit);
                w.WriteEndObject();
            }
            w.WriteEndObject();
        }
    }

    private void Load()
    {
        try
        {
            if (!File.Exists(_storePath)) return;
            using var doc = JsonDocument.Parse(File.ReadAllText(_storePath));
            foreach (var p in doc.RootElement.EnumerateObject())
            {
                var t = p.Value.TryGetProperty("t", out var tv) ? tv.GetInt32() : 0;
                var st = p.Value.TryGetProperty("s", out var sv) ? sv.GetInt32() : 0;
                var l = p.Value.TryGetProperty("l", out var lv) ? lv.GetInt32() : 0;
                _clusters[p.Name] = (t, st, l);
            }
        }
        catch { /* 损坏 → 从零重建 */ }
    }
}
