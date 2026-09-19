namespace agent.files;

/// <summary>
/// 文件服务插件契约 — 与 IImageRenderPlugin 同构: 可替换实现 + 可用性自述。
/// 无可用插件时调用方须诚实报「文件服务不可用」，不得回落到无备份的裸写。
/// </summary>
public interface IFileServicePlugin
{
    /// <summary>插件名（台账/回执口径）。</summary>
    string Name { get; }

    /// <summary>本进程是否可用（依赖/权限自检）。</summary>
    bool IsAvailable { get; }

    /// <summary>按选项建服务实例。</summary>
    IFileService Create(FileServiceOptions options);
}
