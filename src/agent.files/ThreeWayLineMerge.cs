using System;
using System.Collections.Generic;

namespace agent.files;

/// <summary>
/// 行级三方合并（base/ours/theirs）— LCS 匹配锚点 ⇒ 双侧 hunk ⇒ 按 base 坐标归并。
/// 规则: 互不相交的改动各自生效; 相交区两组改动文本相同 ⇒ 取一份; 不同 ⇒ 冲突块（不裁决）。
/// 保守边界: 纯插入落在另一侧改动区边界、或双侧改动相邻但无共同匹配行分隔 ⇒ 判冲突（宁可交人，不静默丢改）。
/// 上限: 任一侧行数 &gt; maxLines ⇒ 返回 null（拒绝自动合并）。
/// </summary>
public static class ThreeWayLineMerge
{
    /// <summary>三方合并；超上限返回 null。</summary>
    public static MergeOutcome? Merge(
        IReadOnlyList<string> baseLines,
        IReadOnlyList<string> oursLines,
        IReadOnlyList<string> theirsLines,
        int maxLines)
    {
        if (baseLines.Count > maxLines || oursLines.Count > maxLines || theirsLines.Count > maxLines)
        {
            return null;
        }

        var hunks = new List<MergeHunk>();
        hunks.AddRange(Hunks(baseLines, oursLines, MergeSide.Ours));
        hunks.AddRange(Hunks(baseLines, theirsLines, MergeSide.Theirs));
        hunks.Sort((a, b) => a.BaseStart != b.BaseStart
            ? a.BaseStart.CompareTo(b.BaseStart)
            : a.BaseEnd.CompareTo(b.BaseEnd));

        var merged = new List<string>();
        var conflicts = new List<FileConflict>();
        var pos = 0;
        var idx = 0;
        while (idx < hunks.Count)
        {
            var clusterStart = hunks[idx].BaseStart;
            var clusterEnd = hunks[idx].BaseEnd;
            var oursLines2 = new List<string>();
            var theirsLines2 = new List<string>();
            var hasOurs = false;
            var hasTheirs = false;
            var k = idx;
            while (k < hunks.Count && Overlaps(clusterStart, clusterEnd, hunks[k].BaseStart, hunks[k].BaseEnd))
            {
                if (hunks[k].Side == MergeSide.Ours)
                {
                    hasOurs = true;
                    oursLines2.AddRange(hunks[k].Lines);
                }
                else
                {
                    hasTheirs = true;
                    theirsLines2.AddRange(hunks[k].Lines);
                }
                if (hunks[k].BaseEnd > clusterEnd)
                {
                    clusterEnd = hunks[k].BaseEnd;
                }
                k++;
            }

            for (var t = pos; t < clusterStart; t++)
            {
                merged.Add(baseLines[t]);
            }

            if (hasOurs && hasTheirs)
            {
                if (SameLines(oursLines2, theirsLines2))
                {
                    merged.AddRange(oursLines2);
                }
                else
                {
                    conflicts.Add(new FileConflict
                    {
                        BaseStartLine = clusterStart,
                        BaseLineCount = clusterEnd - clusterStart,
                        OursText = string.Join("\n", oursLines2),
                        TheirsText = string.Join("\n", theirsLines2),
                    });
                }
            }
            else if (hasOurs)
            {
                merged.AddRange(oursLines2);
            }
            else if (hasTheirs)
            {
                merged.AddRange(theirsLines2);
            }
            else
            {
                for (var t = clusterStart; t < clusterEnd; t++)
                {
                    merged.Add(baseLines[t]);
                }
            }

            pos = clusterEnd;
            idx = k;
        }

        for (var t = pos; t < baseLines.Count; t++)
        {
            merged.Add(baseLines[t]);
        }

        return new MergeOutcome { MergedLines = merged, Conflicts = conflicts };
    }

    /// <summary>单侧改动块: 由 LCS 锚点之间的「空洞」构成（含首尾空洞）。</summary>
    private static List<MergeHunk> Hunks(IReadOnlyList<string> baseLines, IReadOnlyList<string> side, MergeSide which)
    {
        var anchors = Anchors(baseLines, side);
        var hunks = new List<MergeHunk>();
        var bPrev = -1;
        var sPrev = -1;
        foreach (var (bi, si) in anchors)
        {
            Add(hunks, which, bPrev + 1, bi, sPrev + 1, si, side);
            bPrev = bi;
            sPrev = si;
        }
        Add(hunks, which, bPrev + 1, baseLines.Count, sPrev + 1, side.Count, side);
        return hunks;
    }

    private static void Add(
        List<MergeHunk> hunks,
        MergeSide which,
        int bStart,
        int bEnd,
        int sStart,
        int sEnd,
        IReadOnlyList<string> side)
    {
        if (bEnd <= bStart && sEnd <= sStart)
        {
            return;
        }
        var lines = new List<string>();
        for (var t = sStart; t < sEnd; t++)
        {
            lines.Add(side[t]);
        }
        hunks.Add(new MergeHunk { Side = which, BaseStart = bStart, BaseEnd = bEnd, Lines = lines });
    }

    /// <summary>LCS 锚点（base 下标, 该侧下标）— 两侧都「未改动」的行。</summary>
    private static List<(int Base, int Side)> Anchors(IReadOnlyList<string> a, IReadOnlyList<string> b)
    {
        var n = a.Count;
        var m = b.Count;
        var dp = new int[n + 1, m + 1];
        for (var i = n - 1; i >= 0; i--)
        {
            for (var j = m - 1; j >= 0; j--)
            {
                dp[i, j] = string.Equals(a[i], b[j], StringComparison.Ordinal)
                    ? dp[i + 1, j + 1] + 1
                    : Math.Max(dp[i + 1, j], dp[i, j + 1]);
            }
        }

        var res = new List<(int Base, int Side)>();
        var x = 0;
        var y = 0;
        while (x < n && y < m)
        {
            if (string.Equals(a[x], b[y], StringComparison.Ordinal))
            {
                res.Add((x, y));
                x++;
                y++;
            }
            else if (dp[x + 1, y] >= dp[x, y + 1])
            {
                x++;
            }
            else
            {
                y++;
            }
        }
        return res;
    }

    /// <summary>
    /// 两组改动是否落在同一 base 区。零宽插入点只在**严格落在**改动区内部时算重叠（落在区边界 = 前后邻接，
    /// 按 base 坐标排序即可无损拼接）；两个插入点落在同一点 = 重叠。
    /// </summary>
    private static bool Overlaps(int aStart, int aEnd, int bStart, int bEnd)
    {
        if (aStart == aEnd && bStart == bEnd)
        {
            return aStart == bStart;
        }
        if (aStart == aEnd)
        {
            return aStart > bStart && aStart < bEnd;
        }
        if (bStart == bEnd)
        {
            return bStart > aStart && bStart < aEnd;
        }
        return Math.Max(aStart, bStart) < Math.Min(aEnd, bEnd);
    }

    private static bool SameLines(List<string> a, List<string> b)
    {
        if (a.Count != b.Count)
        {
            return false;
        }
        for (var i = 0; i < a.Count; i++)
        {
            if (!string.Equals(a[i], b[i], StringComparison.Ordinal))
            {
                return false;
            }
        }
        return true;
    }
}
