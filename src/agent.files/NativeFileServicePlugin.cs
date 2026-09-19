namespace agent.files;

/// <summary>
/// 内置本地文件服务插件（默认档）— 备份/竞争/合并三保证齐备，AOT 可用、零外部依赖。
/// </summary>
public sealed class NativeFileServicePlugin : IFileServicePlugin
{
    public string Name => "native-local-file-service";

    public bool IsAvailable => true;

    public IFileService Create(FileServiceOptions options) => new LocalFileService(options);
}
