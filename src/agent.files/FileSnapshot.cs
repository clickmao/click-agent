namespace agent.files;

/// <summary>
/// 文件快照 — 竞争判定的锚（sha256 + 字节数 + 最后写入时刻 + 是否存在）。
/// </summary>
public sealed class FileSnapshot
{
    public string Path { get; set; } = string.Empty;

    public bool Exists { get; set; }

    public string Sha256 { get; set; } = string.Empty;

    public long Bytes { get; set; }

    public long LastWriteUtcTicks { get; set; }

    /// <summary>不存在的快照（sha 为空 ⇒ 与任何期望值都不相等）。</summary>
    public static FileSnapshot Missing(string path) => new() { Path = path, Exists = false };
}
