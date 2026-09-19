namespace agent.files;

/// <summary>
/// 三方合并的改动归属侧（base 坐标无关，只标「这组改动来自谁」）。
/// </summary>
public enum MergeSide
{
    /// <summary>现盘一侧（他人/用户已写入的内容）。</summary>
    Ours = 0,

    /// <summary>本次待写一侧（agent 的 NewText）。</summary>
    Theirs = 1,
}
