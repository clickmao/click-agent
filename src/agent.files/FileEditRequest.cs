namespace agent.files;

/// <summary>
/// 写请求 — 乐观并发凭据 ExpectedSha256 由读取方带回（空 = 视为新建/无条件）。
/// </summary>
public sealed class FileEditRequest
{
    public string Path { get; set; } = string.Empty;

    /// <summary>agent 读文件时看到的 sha256（空 = 无条件写，仍先备份）。</summary>
    public string ExpectedSha256 { get; set; } = string.Empty;

    public string NewText { get; set; } = string.Empty;

    /// <summary>基线文本（agent 手上的原文）— 三方合并的 base；null ⇒ 从备份库按 ExpectedSha256 取。</summary>
    public string? BaseText { get; set; }

    /// <summary>来源标记（谁改的：agent 节点 id / 用户 / 工具名）— 落备份索引可追。</summary>
    public string Source { get; set; } = string.Empty;
}
