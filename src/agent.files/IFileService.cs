using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace agent.files;

/// <summary>
/// 文件服务契约（RF0003）— 读带快照、写带备份与竞争判定；实现由插件提供（可替换）。
/// </summary>
public interface IFileService
{
    /// <summary>工作区根目录（相对路径的解析基准，也是沙箱边界）。</summary>
    string Root { get; }

    /// <summary>取现盘快照（竞争判定的锚）。</summary>
    Task<FileSnapshot> SnapshotAsync(string path, CancellationToken ct = default);

    /// <summary>读文本；非文本/不存在返回 null。</summary>
    Task<string?> ReadTextAsync(string path, CancellationToken ct = default);

    /// <summary>带备份与竞争判定的写；返回结果携带写后快照/备份指针/冲突块。</summary>
    Task<FileEditResult> ApplyAsync(FileEditRequest request, CancellationToken ct = default);

    /// <summary>某文件的备份链（时间升序）。</summary>
    IReadOnlyList<FileBackupRecord> ListBackups(string path);

    /// <summary>按备份记录还原（还原也是修改 ⇒ 先备份现盘；备份失败即拒还原，fail-closed）。</summary>
    FileEditResult Restore(FileBackupRecord record);
}
