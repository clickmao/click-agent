using System.Collections.Generic;

namespace agent.files;

/// <summary>
/// 文件服务插件注册表（与 ImageRenderPluginRegistry 同构）— 唯一的插件发现入口。
/// </summary>
public sealed class FileServicePluginRegistry
{
    private readonly List<IFileServicePlugin> _plugins = new();

    public FileServicePluginRegistry(IEnumerable<IFileServicePlugin>? plugins = null)
    {
        if (plugins is not null)
        {
            foreach (var plugin in plugins)
            {
                _plugins.Add(plugin);
            }
        }
        if (_plugins.Count == 0)
        {
            _plugins.Add(new NativeFileServicePlugin());
        }
    }

    /// <summary>全部已注册插件。</summary>
    public IReadOnlyList<IFileServicePlugin> All => _plugins;

    /// <summary>首个可用插件（null = 无可用插件，调用方须诚实报不可用）。</summary>
    public IFileServicePlugin? FirstAvailable()
    {
        foreach (var plugin in _plugins)
        {
            if (plugin.IsAvailable)
            {
                return plugin;
            }
        }
        return null;
    }

    /// <summary>建服务；无可用插件返回 null。</summary>
    public IFileService? Create(FileServiceOptions options)
        => FirstAvailable()?.Create(options);
}
