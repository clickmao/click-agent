namespace agent.files;

/// <summary>
/// 冲突块 — base 行坐标 + 两侧替换文本（供回执/人工裁定，不含自动裁决）。
/// </summary>
public sealed class FileConflict
{
    /// <summary>base 中的起始行号（0 基）。</summary>
    public int BaseStartLine { get; set; }

    /// <summary>被两侧同时改动的 base 行数。</summary>
    public int BaseLineCount { get; set; }

    /// <summary>己方（现盘）在该区的文本。</summary>
    public string OursText { get; set; } = string.Empty;

    /// <summary>对方（本次新文本）在该区的文本。</summary>
    public string TheirsText { get; set; } = string.Empty;
}
