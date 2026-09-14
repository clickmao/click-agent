using System.Text;

namespace agent.session;

/// <summary>
/// 跨会话历史检索 (R370 · L2-F1, 对位宿主侧 session_search 能力)。
///
/// 现状缺口: 会话记忆已落盘 (data/sessions/&lt;id&gt;_memory.json) 但**无任何检索入口**
/// (ISessionMemoryStore 只有 Load/Save)。本组件补上"能存也能查"的另一半。
///
/// 设计约束:
///   1) 确定性: 同一输入 → 同一排序 (score desc, sessionId Ordinal asc), 无随机/无时间因子;
///   2) 零 LLM / 零反射 / AOT 友好: 纯标准库字符统计, 不引入任何模型或序列化;
///   3) 只读: 不改动存储格式, 不写盘;
///   4) 中文友好: CJK 走字符二元组 (与项目既有 trigram/Jaccard 口径同族), ASCII 走词元;
///   5) R422 打分校准: 分母带文档词元数 (余弦式 sqrt|d|) ⇒ 同一词元命中时短文更相关;
///      除数为正 ⇒ 命中集合不变, 只改集合内分档 (R421 真机三份文档同分 0.5596 的零区分度已消除)。
///
/// 诚实边界: 检索面 = 会话记忆摘要 (LongTermMemory / GoalText / KeyEntities /
/// Constraints / Milestones)。逐轮消息当前**未落盘**, 故不在检索面内 (登记为 L3 前置)。
/// </summary>
public sealed class SessionHistorySearch
{
    /// <summary>会话来源端口 (便于测试注入; 生产用 JsonSessionMemoryStore)</summary>
    public interface ISource
    {
        IReadOnlyList<string> EnumerateSessionIds();
        SessionMemory? Load(string sessionId);
    }

    /// <summary>命中项 (排序后)</summary>
    public sealed record Hit(string SessionId, double Score, string Snippet, int EntryCount, int DocChars);

    private readonly ISource _source;
    private readonly int _snippetChars;

    public SessionHistorySearch(ISource source, int snippetChars = 120)
    {
        _source = source ?? throw new ArgumentNullException(nameof(source));
        _snippetChars = snippetChars < 32 ? 32 : snippetChars;
    }

    /// <summary>
    /// 检索会话历史。空查询/无命中 → 空列表 (不抛异常)。
    /// </summary>
    public IReadOnlyList<Hit> Search(string query, int topK = 5, double minScore = 0.0)
    {
        if (string.IsNullOrWhiteSpace(query) || topK <= 0)
            return Array.Empty<Hit>();

        var qTokens = Tokenize(query);
        if (qTokens.Count == 0)
            return Array.Empty<Hit>();
        var qNorm = Normalize(query);
        var qSet = new HashSet<string>(qTokens, StringComparer.Ordinal);

        // 1) 先取全部会话的文档 (避免二次 Load)
        var docs = new List<(string Id, string Text, string Norm, HashSet<string> Tokens, int Entries, int Chars)>();
        foreach (var id in _source.EnumerateSessionIds())
        {
            if (string.IsNullOrWhiteSpace(id))
                continue;
            var mem = _source.Load(id);
            if (mem == null)
                continue;
            var text = BuildDocument(mem);
            if (text.Length == 0)
                continue;
            var norm = Normalize(text);
            docs.Add((id, text, norm, new HashSet<string>(Tokenize(text), StringComparer.Ordinal), mem.EntryCount, text.Length));
        }
        if (docs.Count == 0)
            return Array.Empty<Hit>();

        // 2) IDF: 出现越广的词权重越低 (单人会话库时不放大)
        var df = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var d in docs)
            foreach (var t in d.Tokens)
                if (qSet.Contains(t))
                    df[t] = df.TryGetValue(t, out var c) ? c + 1 : 1;
        var n = docs.Count;
        double Idf(string t) => Math.Log(1.0 + (double)n / (1 + (df.TryGetValue(t, out var d) ? d : 0)));

        // 3) 打分
        var hits = new List<Hit>();
        foreach (var d in docs)
        {
            double score = 0;
            foreach (var t in qSet)
                if (d.Tokens.Contains(t))
                    score += Idf(t);
            if (score <= 0 && qNorm.Length >= 4 && d.Norm.Contains(qNorm, StringComparison.Ordinal))
                score = 1.0;   // 整串命中兜底 (分词切不出的长串)
            else if (qNorm.Length >= 4 && d.Norm.Contains(qNorm, StringComparison.Ordinal))
                score += 2.0;  // 整串命中加成

            // R422: 文档长度归一 (余弦式分母 sqrt|d.Tokens|)。同一词元命中时, 词元数少的文档更相关。
            // 依据: R421 真机三份命中文档分数**全等** (0.5596) ⇒ 命中集合内零区分度 (短文/长文不分)。
            // 除数为正 ⇒ **不改分数符号** ⇒ 命中集合逐元素不变, 只改集合内分档与排序 (成对判据见 r422 harness)。
            score /= Math.Sqrt(qSet.Count) * Math.Sqrt(Math.Max(1, d.Tokens.Count));
            if (score <= minScore || score <= 0)
                continue;
            hits.Add(new Hit(d.Id, Math.Round(score, 6), Snippet(d.Text, qSet), d.Entries, d.Chars));
        }

        // 4) 稳定排序: score desc → sessionId Ordinal asc (确定性)
        hits.Sort((a, b) =>
        {
            var c = b.Score.CompareTo(a.Score);
            return c != 0 ? c : string.CompareOrdinal(a.SessionId, b.SessionId);
        });
        return hits.Count <= topK ? hits : hits.GetRange(0, topK);
    }

    /// <summary>检索面文本 (会话记忆摘要; 逐轮消息未落盘故不在内)</summary>
    public static string BuildDocument(SessionMemory memory)
    {
        var sb = new StringBuilder();
        if (memory.Goal != null)
        {
            if (!string.IsNullOrWhiteSpace(memory.Goal.GoalText))
                sb.Append(memory.Goal.GoalText).Append('\n');
            if (memory.Goal.KeyEntities.Count > 0)
                sb.Append(string.Join('、', memory.Goal.KeyEntities)).Append('\n');
            if (memory.Goal.Constraints.Count > 0)
                sb.Append(string.Join("; ", memory.Goal.Constraints)).Append('\n');
            if (memory.Goal.Milestones.Count > 0)
                sb.Append(string.Join("; ", memory.Goal.Milestones)).Append('\n');
        }
        if (!string.IsNullOrEmpty(memory.LongTermMemory))
            sb.Append(memory.LongTermMemory);
        return sb.ToString().Trim();
    }

    /// <summary>取命中上下文片段: 命中词最多的一行, 截断到 snippetChars</summary>
    private string Snippet(string text, HashSet<string> qSet)
    {
        string best = text;
        int bestHits = -1;
        foreach (var raw in text.Split('\n'))
        {
            var line = raw.Trim();
            if (line.Length == 0)
                continue;
            var lineTokens = Tokenize(line);
            var h = 0;
            foreach (var t in lineTokens)
                if (qSet.Contains(t))
                    h++;
            if (h > bestHits)
            {
                bestHits = h;
                best = line;
            }
        }
        best = best.Trim();
        if (best.Length <= _snippetChars)
            return best;
        // 命中词为中心开窗 (否则长行头部截断会把命中词截掉, 片段等于没给证据)
        var idx = -1;
        foreach (var t in qSet)
        {
            var p = best.IndexOf(t, StringComparison.Ordinal);
            if (p >= 0 && (idx < 0 || p < idx))
                idx = p;
        }
        if (idx < 0)
            return best[.._snippetChars] + "…";
        var start = Math.Max(0, idx - _snippetChars / 3);
        if (start + _snippetChars > best.Length)
            start = Math.Max(0, best.Length - _snippetChars);
        var slice = best.Substring(start, Math.Min(_snippetChars, best.Length - start)).Trim();
        return (start > 0 ? "…" : "") + slice + (start + slice.Length < best.Length ? "…" : "");
    }

    /// <summary>归一化: ASCII 小写; 丢弃空白与控制字符 (CJK 原样保留)</summary>
    internal static string Normalize(string s)
    {
        var sb = new StringBuilder(s.Length);
        foreach (var ch in s)
        {
            if (ch <= ' ' || char.IsControl(ch))
                continue;
            sb.Append(char.ToLowerInvariant(ch));
        }
        return sb.ToString();
    }

    /// <summary>
    /// 否定极性前缀 (R421): 由否定标记衍生出的二元组带此前缀 ⇒ 与肯定二元组**不互 match**。
    /// 用 U+0001 (Normalize 会丢弃全部控制字符 ⇒ 真实文本不可能产出该前缀 ⇒ 无碰撞)。
    /// </summary>
    internal const char NegMark = '\u0001';

    /// <summary>
    /// 否定标记 (R421)。取 5 个典型否定语素; **刻意不含** 别/勿/莫/甭 ——
    /// 「识别/区别/特别」等高频非否定用法会与其碰撞, 收益(禁阻式罕见) 不抵成本。
    /// </summary>
    private static bool IsNegationMark(char c) => c is '不' or '没' or '未' or '无' or '非';

    /// <summary>词元: ASCII/数字词 (≥2 字符) + CJK 相邻二元组</summary>
    internal static List<string> Tokenize(string s)
    {
        var norm = Normalize(s);
        var tokens = new List<string>();
        var word = new StringBuilder();
        void FlushWord()
        {
            if (word.Length >= 2)
                tokens.Add(word.ToString());
            word.Clear();
        }
        for (var i = 0; i < norm.Length; i++)
        {
            var ch = norm[i];
            if (IsWordChar(ch))
            {
                word.Append(ch);
            }
            else
            {
                FlushWord();
                if (IsCjk(ch) && i + 1 < norm.Length && IsCjk(norm[i + 1]))
                {
                    // R421 极性: 否定标记自身及其紧邻的下一个二元组带否定极性。
                    // 依据: "不存在" 的二元组含 "存在" ⇒ 不做极性区分时, 否定查询会召回到
                    // 只断言肯定命题的文档, 读起来像**肯定** (R420 真机暴露: 存在/不存在 命中同一批)。
                    // 边界(诚实): 极性作用域 = 标记 + 其紧邻的 **1 个**二元组, 不做从句级推导。
                    var negated = IsNegationMark(ch) || (i > 0 && IsNegationMark(norm[i - 1]));
                    var raw = new string(new[] { ch, norm[i + 1] });
                    tokens.Add(negated ? NegMark + raw : raw);
                }
            }
        }
        FlushWord();
        return tokens;
    }

    private static bool IsWordChar(char c) => c < 128 && (char.IsLetterOrDigit(c) || c is '_' or '-');

    private static bool IsCjk(char c) => c >= 0x4E00 && c <= 0x9FFF;

    /// <summary>
    /// 命中项渲染为本地指令回复 (纯文本, 零 LLM/零反射)。
    /// 空命中 → 显式"无命中"文案 (失败可见: 空结果也必须有可读回执, 不静默空白)。
    /// </summary>
    public static string Render(IReadOnlyList<Hit> hits, string query, int topK)
    {
        var sb = new StringBuilder();
        sb.Append("🔎 跨会话检索 \"").Append(query).Append("\" (top-").Append(topK)
          .Append(", 命中 ").Append(hits.Count).AppendLine("):");
        if (hits.Count == 0)
        {
            sb.Append("(无命中 — 检索面 = 已落盘会话记忆摘要: 目标/长期记忆/关键实体/约束/里程碑)");
            return sb.ToString();
        }
        var rank = 0;
        foreach (var h in hits)
        {
            rank++;
            sb.Append(rank).Append(". ").Append(h.SessionId)
              .Append("  score=").Append(h.Score.ToString("F4", System.Globalization.CultureInfo.InvariantCulture))
              .Append("  entries=").Append(h.EntryCount).AppendLine();
            sb.Append("   …").Append(h.Snippet).AppendLine();
        }
        return sb.ToString();
    }

    /// <summary>生产实现: 包装 JsonSessionMemoryStore (data/sessions/)</summary>
    public sealed class StoreSource : ISource
    {
        private readonly JsonSessionMemoryStore _store;

        public StoreSource(string dataStoragePath = "data")
            => _store = new JsonSessionMemoryStore(dataStoragePath);

        public StoreSource(JsonSessionMemoryStore store)
            => _store = store ?? throw new ArgumentNullException(nameof(store));

        public IReadOnlyList<string> EnumerateSessionIds() => _store.EnumerateSessionIds();

        public SessionMemory? Load(string sessionId) => _store.Load(sessionId);
    }
}
