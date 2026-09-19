namespace agent.files;

/// <summary>
/// RF0003 文件插件服务选项 — 备份/竞争/合并三条硬保证的开关与上限。
/// </summary>
public sealed class FileServiceOptions
{
    /// <summary>工作区根目录（null = 进程当前目录）；相对路径一律相对它解析，越界路径拒写。</summary>
    public string? WorkspaceRoot { get; set; }

    /// <summary>备份库根目录（null = &lt;工作区根&gt;/.filedb）。</summary>
    public string? BackupRoot { get; set; }

    /// <summary>每个原文件保留的备份条数（超出按时间淘汰）。</summary>
    public int KeepPerFile { get; set; } = 20;

    /// <summary>强制备份: true = 备份失败即拒绝写入（fail-closed，默认）。</summary>
    public bool RequireBackup { get; set; } = true;

    /// <summary>允许三方合并: false = 现盘变更一律 StaleBase（不写）。</summary>
    public bool AllowMerge { get; set; } = true;

    /// <summary>三方合并行数上限（任一侧超过 ⇒ 拒绝自动合并，交人工）。</summary>
    public int MaxMergeLines { get; set; } = 2000;
}
