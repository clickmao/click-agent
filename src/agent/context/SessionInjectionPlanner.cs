using System.Text;

namespace agent.context;

/// <summary>
/// R379 会话提示注入规划器 —— 面向 provider 上下文缓存的「增量最小化」。
///
/// 实测前提 (DeepSeek KV cache 官方规则): 缓存单元 = 64 token, 必须自 token 0 起完整匹配缓存前缀单元才命中。
/// 推论: 命中率 ≈ 已发前缀 token / 本轮总 token。所以只有两条路能抬高命中率 ——
///   ① 会话前缀内的字节**永不改写**(追加式); ② 每轮新增字节**尽可能少**。
///
/// 本类只做判据、不碰业务:
///   1. 把每轮重建的上下文头按块头 '[' 切块;
///   2. 标出【会话静态块】(画像/偏好/工作区等, 会话内几乎不变) → 只在会话首轮进前缀;
///   3. 对【动态块】做跨轮**行级去重**(已发过的行不再重复注入 —— 历史里已有, 信息不丢)。
/// </summary>
public static class SessionInjectionPlanner
{
    /// <summary>会话静态块标题前缀白名单 (命中即视为会话内近静态)。</summary>
    private static readonly string[] StaticTitlePrefixes =
    {
        "AgentContext", "Agent 画像", "可用能力", "User Preference", "Workspace Files", "工作区文件",
    };

    /// <summary>
    /// 参与去重的最短行长度: 8 (短行如 "-" "1." 之类噪声多, 不参与去重以免误伤结构)。
    /// 实测标定: 真实上下文块的行多 ≥8 (如 "Q: 二分查找的前提?" 11 字符), 阈值 12 会让大量真实行漏拿去重。
    /// </summary>
    public const int MinDedupeLineLength = 8;

    /// <summary>去重行哈希集合的上界 (超过即清空, 防长驻进程无界增长)。</summary>
    public const int MaxTrackedLines = 20000;

    /// <summary>
    /// 近重复判据 (trigram Jaccard)。实测标定 (真机 3 轮 dump):
    /// 轮 3 的召回块里 59/48/56 字符三行与轮 1 的旧行 jac=0.77~0.79 (措辞微改、语义重复) ——
    /// 字节级去重抓不到, 但模型在历史里已看过等价内容, 重复发送纯属白烧 prefix 增量。
    /// </summary>
    public const double NearDupThreshold = 0.75;

    /// <summary>近重复比对的历史行上限 (取最近若干, 控 O(n·m) 开销)。</summary>
    public const int MaxComparedBodies = 600;

    /// <summary>
    /// 跨轮注入账本: 记录本会话**已注入过**的上下文行。
    /// 判据零业务耦合 —— 只认"发过的字节/近似字节", 不认内容语义。
    /// </summary>
    public sealed class InjectionLedger
    {
        private readonly HashSet<string> _hashes = new(StringComparer.Ordinal);
        private readonly List<string> _bodies = new();

        public int Count => _hashes.Count;

        public bool Contains(string line) => _hashes.Contains(Fnv1a(line));

        public void Add(string line)
        {
            _hashes.Add(Fnv1a(line));
            if (_bodies.Count < MaxComparedBodies) _bodies.Add(line);
        }

        /// <summary>与历史已发行的最大 trigram Jaccard (无历史 → 0)。</summary>
        public double MaxSimilarity(string line)
        {
            var best = 0.0;
            foreach (var prev in _bodies)
            {
                var j = Similarity(line, prev);
                if (j > best) best = j;
                if (best >= 1.0) break;
            }
            return best;
        }

        public void Clear() { _hashes.Clear(); _bodies.Clear(); }
    }

    /// <summary>trigram Jaccard 相似度 (空白折叠; 任一为空 → 0)。</summary>
    public static double Similarity(string a, string b)
    {
        var ta = Trigrams(a);
        var tb = Trigrams(b);
        if (ta.Count == 0 || tb.Count == 0) return 0.0;
        var inter = 0;
        foreach (var t in ta) if (tb.Contains(t)) inter++;
        return (double)inter / (ta.Count + tb.Count - inter);
    }

    private static HashSet<string> Trigrams(string s)
    {
        var set = new HashSet<string>(StringComparer.Ordinal);
        var buf = new StringBuilder(s.Length);
        foreach (var ch in s) if (!char.IsWhiteSpace(ch)) buf.Append(ch);
        var t = buf.ToString();
        for (var i = 0; i + 3 <= t.Length; i++) set.Add(t.Substring(i, 3));
        return set;
    }

    /// <summary>上下文块 (Title = 块头 '[' 内文本, Text = 含块头的整块文本)。</summary>
    public sealed record Block(string Title, string Text);

    public static bool IsSessionStatic(string title)
    {
        foreach (var p in StaticTitlePrefixes)
            if (title.StartsWith(p, StringComparison.Ordinal))
                return true;
        return false;
    }

    /// <summary>按行首 '[' 切块; 首个块头之前的前导文本归入标题 ""。</summary>
    public static List<Block> Split(string? header)
    {
        var result = new List<Block>();
        if (string.IsNullOrWhiteSpace(header)) return result;

        var lines = header.Replace("\r\n", "\n").Split('\n');
        var title = string.Empty;
        var buf = new List<string>();

        void Flush()
        {
            var text = string.Join("\n", buf).TrimEnd();
            if (text.Length > 0) result.Add(new Block(title, text));
            buf.Clear();
        }

        foreach (var line in lines)
        {
            var t = line.TrimStart();
            if (t.StartsWith('[') && t.Contains(']'))
            {
                Flush();
                title = t[1..t.IndexOf(']')];
            }
            buf.Add(line);
        }
        Flush();
        return result;
    }

    /// <summary>把块拼回文本 (块间空行分隔)。</summary>
    public static string Join(IEnumerable<Block> blocks)
        => string.Join("\n\n", blocks.Select(b => b.Text).Where(t => t.Length > 0));

    /// <summary>
    /// 跨轮行级去重 + 近重复抑制 (账本由调用方持有并跨轮复用)。
    /// 丢弃判据: ① 该行字节已注入过; ② 该行与历史已发行的 trigram Jaccard ≥ NearDupThreshold (语义重复)。
    /// 块头行恒保留 (否则块语义丢失); **用户本轮原始问题永不经过本方法** (调用方只传上下文块)。
    /// 返回 (保留文本, 保留行数, 丢弃行数)。
    /// </summary>
    public static (string Text, int Kept, int Dropped) Dedupe(IEnumerable<Block> blocks, InjectionLedger ledger)
    {
        var sb = new StringBuilder();
        var kept = 0;
        var dropped = 0;

        foreach (var b in blocks)
        {
            var body = new List<string>();
            var lines = b.Text.Split('\n');
            for (var i = 0; i < lines.Length; i++)
            {
                var key = lines[i].Trim();
                if (i > 0 && key.Length >= MinDedupeLineLength)
                {
                    if (ledger.Contains(key) || ledger.MaxSimilarity(key) >= NearDupThreshold)
                    {
                        dropped++;
                        continue;
                    }
                    ledger.Add(key);
                }
                body.Add(lines[i]);
                kept++;
            }
            if (body.Count > 0) sb.Append(string.Join("\n", body)).Append("\n\n");
        }

        if (ledger.Count > MaxTrackedLines) ledger.Clear();   // 有界: 防无界增长
        return (sb.ToString().TrimEnd(), kept, dropped);
    }

    /// <summary>行哈希 (FNV-1a 32bit — 与仓库既有 ClusterKey 口径一致, 零依赖、确定性)。</summary>
    internal static string Fnv1a(string s)
    {
        unchecked
        {
            var h = 2166136261u;
            foreach (var ch in s)
            {
                h ^= (byte)(ch & 0xFF);
                h *= 16777619u;
                h ^= (byte)(ch >> 8);
                h *= 16777619u;
            }
            return h.ToString("x8");
        }
    }
}
