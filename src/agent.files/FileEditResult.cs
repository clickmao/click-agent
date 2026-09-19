using System.Collections.Generic;

namespace agent.files;

/// <summary>
/// 写结果 — 携带写后快照、备份指针与冲突块（供台账/回执；冲突时 MergedText 仅供展示）。
/// </summary>
public sealed class FileEditResult
{
    public FileEditOutcome Outcome { get; set; }

    public string Path { get; set; } = string.Empty;

    /// <summary>写盘后（或判定时）的现盘快照。</summary>
    public FileSnapshot? Snapshot { get; set; }

    /// <summary>写盘前落下的备份 blob 路径（Applied/MergedAuto 必有）。</summary>
    public string? BackupPath { get; set; }

    /// <summary>写盘前落下的备份内容 sha256（即被覆盖的那一版）。</summary>
    public string? BackupSha256 { get; set; }

    /// <summary>合并/冲突展示文本（Conflict 时含两侧标记）。</summary>
    public string? MergedText { get; set; }

    /// <summary>冲突块（Conflict 时非空）。</summary>
    public List<FileConflict> Conflicts { get; set; } = new();

    /// <summary>判定说明（机检与回执用；不含自由叙述）。</summary>
    public string Note { get; set; } = string.Empty;

    /// <summary>是否真的写了盘 —— 只有两类为 true。</summary>
    public bool Wrote => Outcome is FileEditOutcome.Applied or FileEditOutcome.MergedAuto;
}
