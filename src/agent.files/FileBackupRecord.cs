namespace agent.files;

/// <summary>
/// 备份记录（索引行）— 内容寻址 blob + 原路径 + 来源，可追可还原。
/// </summary>
public sealed class FileBackupRecord
{
    public string Sha256 { get; set; } = string.Empty;

    public long Bytes { get; set; }

    /// <summary>被备份的原文件绝对路径。</summary>
    public string OriginalPath { get; set; } = string.Empty;

    /// <summary>备份时刻（UTC ticks）。</summary>
    public long TakenUtcTicks { get; set; }

    /// <summary>blob 绝对路径（内容寻址）。</summary>
    public string BlobPath { get; set; } = string.Empty;

    /// <summary>来源标记（agent 节点 / 用户 / 工具名）。</summary>
    public string Source { get; set; } = string.Empty;
}
