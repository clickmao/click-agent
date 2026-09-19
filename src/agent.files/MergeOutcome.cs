using System.Collections.Generic;

namespace agent.files;

/// <summary>
/// 三方合并产物 — 合并文本 + 冲突块（Clean = 无冲突，可安全落盘）。
/// </summary>
public sealed class MergeOutcome
{
    public List<string> MergedLines { get; set; } = new();

    public List<FileConflict> Conflicts { get; set; } = new();

    /// <summary>无冲突（可以落盘）。</summary>
    public bool Clean => Conflicts.Count == 0;
}
