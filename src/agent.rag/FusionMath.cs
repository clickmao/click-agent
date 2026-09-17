using System;
using System.Collections.Generic;

namespace agent.rag;


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
