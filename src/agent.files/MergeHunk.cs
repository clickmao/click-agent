using System.Collections.Generic;

namespace agent.files;

/// <summary>
/// 单侧改动块（base 坐标区间 + 该侧替换行）。
/// </summary>
public sealed class MergeHunk
{
    public MergeSide Side { get; set; }

    /// <summary>base 中起始行（0 基，含）。</summary>
    public int BaseStart { get; set; }

    /// <summary>base 中结束行（不含）；BaseStart == BaseEnd ⇒ 纯插入。</summary>
    public int BaseEnd { get; set; }

    /// <summary>该侧在此区间的替换行（空 = 纯删除）。</summary>
    public List<string> Lines { get; set; } = new();
}
