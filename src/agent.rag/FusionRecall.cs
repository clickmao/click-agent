using System;
using System.Collections.Generic;

namespace agent.rag;

/// <summary>
/// R404 (用户钦定): 检索融合 —— "优化后的 bge" 的落地形态 (端口化)。
///
/// 依据 (冻结集 1299 语料 / 120 查询, 证据 eval/bge/, 报告 docs/reports/bge/):
///   • 单路 dense-small (链上真身 = 25.2MB bge-small-zh-v1.5 q8)  r@10 0.6333
///   • 单路词法路 (字符二元组 Jaccard)                             r@10 0.7500
///   • **RRF(词法 + dense-small, k0=10, w=1:1) ← 本类·产品口径**   r@10 0.7833  (+18 条查询, 配对 p=4e-05)
///   • [评测对照·非产品] 单路 dense-base (110MB)                   r@10 0.7417
///   • [评测对照·非产品] RRF(词法 + dense-base, 同超参)             r@10 0.8500  (+13 条 vs dense-base 本身)
///     —— 该权重已按用户令(2026-09-14)从本机删除; 其向量缓存保留 ⇒ 读数仍可从缓存复现, 但不能再跑前向。
///   • 三路 union 上界 (含 dense-small)                            r@10 0.8667  ⇒ 融合已吃 98%, 同族第三路零增益
///
/// 口径纪律: 词法打分与 RRF 算术与 eval/bge/fusion.py **逐式对齐**(独立实现交叉对账),
/// 任何"看起来更好"的改动都必须先过该冻结集 —— 机检 src/agent.tests/RagFusionTests.cs。
///
/// AOT: 零反射 / 零 shell / 零外部进程; 计数可查 (routes_used / dim_skipped / fallback —— 防空心判定)。
/// </summary>
public sealed class FusionOptions
{
    public bool Enabled { get; set; } = true;

    /// <summary>RRF 平滑常数 (冻结值 10; 网格实验证明 k0∈{1,5,60} 与权重扰动最多 +1 条且 r@1 反降)。</summary>
    public int K0 { get; set; } = 10;

    public double DenseWeight { get; set; } = 1.0;
    public double LexicalWeight { get; set; } = 1.0;
}

/// <summary>检索候选 (文档侧一行)。<see cref="Bigrams"/> 可外部注入 (记忆化), 未注入则惰性计算。</summary>
public sealed class RetrievalCandidate
{
    public string Id = string.Empty;
    public string Text = string.Empty;
    public float[]? Embedding;

    private string[]? _bigrams;

    /// <summary>去空白字符二元组集合 (与 eval/bge/fusion.py 的 grams() 同口径)。</summary>
    public string[] Bigrams
    {
        get => _bigrams ??= FusionMath.CharacterBigrams(Text);
        set => _bigrams = value;
    }
}

/// <summary>查询侧上下文 (原文 + 已算好的查询向量, 可为 null ⇒ 该路自行降级)。</summary>
public readonly struct QueryContext
{
    public QueryContext(string text, float[]? embedding)
    {
        Text = text ?? string.Empty;
        Embedding = embedding;
    }

    public string Text { get; }
    public float[]? Embedding { get; }
}

/// <summary>可替换执行面端口: 一路检索对同一批候选给出 0 起名次 (与 eval/bge 的秩数组同口径)。</summary>
public interface IRetrievalRoute
{
    string Name { get; }

    /// <summary>返回长度 == candidates.Count 的秩数组; ranks[d] = 文档 d 的 0 起名次。</summary>
    int[] Rank(QueryContext query, IReadOnlyList<RetrievalCandidate> candidates);
}

/// <summary>融合路数打点 (证据: 每路真实被用次数 + 降级/跳过次数 —— 防"空心端口")。</summary>
public sealed class FusionCounters
{
    public long FusionCalls;
    public long DenseUsed;
    public long LexicalUsed;
    public long SingleRouteFallback;
    public long DimMismatchSkipped;
    public long CandidatesScored;
    public long BigramMemoHits;

    public void Reset()
    {
        FusionCalls = DenseUsed = LexicalUsed = SingleRouteFallback = 0;
        DimMismatchSkipped = CandidatesScored = BigramMemoHits = 0;
    }
}

/// <summary>词法/融合的纯函数算术 (无状态, 可单测)。</summary>
public static class FusionMath
{
    /// <summary>去空白字符的 2-gram 集合 (Python: "".join(c for c in s if not c.isspace()) 后滑窗)。

    /// 注意: 空白被**移除**而不是当分隔符 —— 跨空白仍成对, 与 Python 逐字符一致。</summary>
    public static string[] CharacterBigrams(string s)
    {
        var set = new HashSet<string>(StringComparer.Ordinal);
        if (string.IsNullOrEmpty(s)) return Array.Empty<string>();
        var prev = '\0';
        var has = false;
        var buf = new char[2];
        for (var i = 0; i < s.Length; i++)
        {
            var ch = s[i];
            if (char.IsWhiteSpace(ch)) continue;
            if (has)
            {
                buf[0] = prev;
                buf[1] = ch;
                set.Add(new string(buf));
            }
            prev = ch;
            has = true;
        }
        return set.Count == 0 ? Array.Empty<string>() : new List<string>(set).ToArray();
    }

    /// <summary>Jaccard: |q∩d| / |q∪d| (Python lexical_scores 同式; 并集为 0 记 0)。
    /// 只收 <paramref name="qset"/> (查询侧去重集合) 与 <paramref name="dgrams"/> —— 不再收一份
    /// 冗余的 qgrams (曾因两者不配套而让"空查询"用例静默算成 1.0)。</summary>
    public static double Jaccard(HashSet<string> qset, string[] dgrams)
    {
        if (qset.Count == 0 || dgrams.Length == 0) return 0.0;
        var inter = 0;
        for (var i = 0; i < dgrams.Length; i++)
            if (qset.Contains(dgrams[i])) inter++;
        var union = qset.Count + dgrams.Length - inter;
        return union == 0 ? 0.0 : (double)inter / union;
    }

    /// <summary>名次: 分数降序, **同分按文档索引降序** —— 复刻冻结实现 eval/bge/fusion.py
    /// 的 order_key (`sorted(range(n), key=lambda i: (-sc[i], -i))`)。两边的 tie-break 必须
    /// 逐字一致, 否则边界名次会漂 (逐位对账会红)。
    /// 注意: RRF 融合输出的排序用的是**另一套** tie-break (索引升序, 见 RrfFuser 调用处,
    /// 对应 Python rrf_all 的 `key=lambda i: (-sc[i], i)`) —— 二者故意不同, 不可"统一"。</summary>
    public static void AssignRanks(double[] scores, int[] ranks)
    {
        var n = scores.Length;
        var idx = new int[n];
        for (var i = 0; i < n; i++) idx[i] = i;
        Array.Sort(idx, (a, b) =>
        {
            var c = scores[b].CompareTo(scores[a]);
            return c != 0 ? c : b.CompareTo(a);
        });
        for (var r = 0; r < n; r++) ranks[idx[r]] = r;
    }

    public static double Cosine(float[] a, float[] b)
    {
        double dot = 0, na = 0, nb = 0;
        for (var i = 0; i < a.Length; i++)
        {
            dot += (double)a[i] * b[i];
            na += (double)a[i] * a[i];
            nb += (double)b[i] * b[i];
        }
        var den = Math.Sqrt(na) * Math.Sqrt(nb);
        return den <= 0 ? 0.0 : dot / den;
    }
}

/// <summary>语义路: 查询向量 × 候选向量 余弦。维度不匹配的候选 (旧 512 维残留) 记 0 分并计数。</summary>
public sealed class DenseRoute : IRetrievalRoute
{
    public string Name => "dense";

    public long Scored { get; private set; }
    public long SkippedDimMismatch { get; private set; }

    public int[] Rank(QueryContext query, IReadOnlyList<RetrievalCandidate> candidates)
    {
        var n = candidates.Count;
        var ranks = new int[n];
        var scores = new double[n];
        var qv = query.Embedding;
        if (qv is null || qv.Length == 0)
        {
            for (var i = 0; i < n; i++) ranks[i] = i;   // 无查询向量 ⇒ 该路退化为文档序
            return ranks;
        }
        for (var i = 0; i < n; i++)
        {
            var dv = candidates[i].Embedding;
            if (dv is null || dv.Length != qv.Length)
            {
                scores[i] = double.NegativeInfinity;
                SkippedDimMismatch++;
                continue;
            }
            scores[i] = FusionMath.Cosine(qv, dv);
            Scored++;
        }
        FusionMath.AssignRanks(scores, ranks);
        return ranks;
    }
}

/// <summary>词法路: 字符二元组 Jaccard (无需向量, 因此旧维度残留文档仍可参与)。</summary>
public sealed class LexicalRoute : IRetrievalRoute
{
    public string Name => "lexical";

    public long Scored { get; private set; }

    public int[] Rank(QueryContext query, IReadOnlyList<RetrievalCandidate> candidates)
    {
        var n = candidates.Count;
        var ranks = new int[n];
        var scores = new double[n];
        var qgrams = FusionMath.CharacterBigrams(query.Text);
        var qset = new HashSet<string>(qgrams, StringComparer.Ordinal);
        for (var i = 0; i < n; i++)
        {
            scores[i] = FusionMath.Jaccard(qset, candidates[i].Bigrams);
            Scored++;
        }
        FusionMath.AssignRanks(scores, ranks);
        return ranks;
    }
}

/// <summary>RRF 融合器: score[d] = Σ_r w_r / (k0 + rank_r[d] + 1) (与 eval/bge 冻结算术同式)。</summary>
public sealed class RrfFuser
{
    private readonly int _k0;

    public RrfFuser(int k0) => _k0 = k0;

    public double[] Scores(IReadOnlyList<int[]> rankLists, IReadOnlyList<double> weights, int candidateCount)
    {
        var scores = new double[candidateCount];
        for (var r = 0; r < rankLists.Count; r++)
        {
            var w = weights[r];
            var rl = rankLists[r];
            for (var d = 0; d < candidateCount; d++)
                scores[d] += w / (_k0 + rl[d] + 1);
        }
        return scores;
    }

    /// <summary>理论满分 (所有路都排第 0) —— 用于把分数线性归一到 0..1, 以便与既有阈值口径共存。</summary>
    public double MaxScore(IReadOnlyList<double> weights)
    {
        var m = 0.0;
        for (var r = 0; r < weights.Count; r++) m += weights[r] / (_k0 + 1);
        return m;
    }
}

/// <summary>
/// 融合召回编排: 候选池 → 各路名次 → RRF 分数 → 降序结果。
/// 单路可用时显式降级并计数 (绝不静默把单路当融合)。
/// </summary>
public sealed class FusionRecall
{
    private readonly FusionOptions _opt;
    private readonly RrfFuser _fuser;
    private readonly IRetrievalRoute? _dense;
    private readonly IRetrievalRoute? _lexical;

    public FusionRecall(FusionOptions options, IRetrievalRoute? dense = null, IRetrievalRoute? lexical = null)
    {
        _opt = options ?? new FusionOptions();
        _fuser = new RrfFuser(_opt.K0);
        _dense = dense;
        _lexical = lexical;
    }

    public FusionCounters Counters { get; } = new();

    /// <summary>返回按融合分降序的 (候选, 分数) 列表; 分数为原始 RRF 分 (未归一)。</summary>
    public List<KeyValuePair<RetrievalCandidate, double>> Rank(
        QueryContext query, IReadOnlyList<RetrievalCandidate> candidates)
    {
        var outList = new List<KeyValuePair<RetrievalCandidate, double>>(candidates.Count);
        if (candidates.Count == 0) return outList;

        var rankLists = new List<int[]>(2);
        var weights = new List<double>(2);

        var denseOk = _dense is not null;
        var lexOk = _lexical is not null;

        if (denseOk) rankLists.Add(_dense!.Rank(query, candidates));
        if (lexOk) rankLists.Add(_lexical!.Rank(query, candidates));

        if (rankLists.Count == 0) return outList;
        if (rankLists.Count == 1)
        {
            Counters.SingleRouteFallback++;
            weights.Add(denseOk ? _opt.DenseWeight : _opt.LexicalWeight);
        }
        else
        {
            weights.Add(_opt.DenseWeight);
            weights.Add(_opt.LexicalWeight);
        }

        Counters.FusionCalls++;
        if (denseOk) Counters.DenseUsed++;
        if (lexOk) Counters.LexicalUsed++;
        Counters.CandidatesScored += candidates.Count;

        var scores = _fuser.Scores(rankLists, weights, candidates.Count);
        var order = new int[candidates.Count];
        for (var i = 0; i < order.Length; i++) order[i] = i;
        Array.Sort(order, (a, b) =>
        {
            var c = scores[b].CompareTo(scores[a]);
            return c != 0 ? c : a.CompareTo(b);
        });
        for (var i = 0; i < order.Length; i++)
            outList.Add(new KeyValuePair<RetrievalCandidate, double>(candidates[order[i]], scores[order[i]]));
        return outList;
    }

    /// <summary>原始 RRF 分的理论满分 (归一化用)。</summary>
    public double MaxScore()
    {
        var w = new List<double>(2);
        if (_dense is not null) w.Add(_opt.DenseWeight);
        if (_lexical is not null) w.Add(_opt.LexicalWeight);
        return _fuser.MaxScore(w);
    }
}
