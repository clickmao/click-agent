using agent.files;

namespace agent.tests;

/// <summary>
/// R584 负控桩: 声明不可用的文件服务插件 —— 用于证明注册表不会在无可用插件时静默回落。
/// </summary>
public sealed class UnavailableFileServicePlugin : IFileServicePlugin
{
    public string Name => "unavailable-stub";

    public bool IsAvailable => false;

    public IFileService Create(FileServiceOptions options) => new LocalFileService(options);
}
