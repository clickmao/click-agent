using System.Text;

namespace agent.modelqueue;


/// <summary>渲染插件注册表 — 按优先级探测可用插件; 全不可用 → HasRenderer=false (上游跳过收敛环)。</summary>
public sealed class ImageRenderPluginRegistry
{
    private readonly List<IImageRenderPlugin> _plugins;
    public ImageRenderPluginRegistry(IEnumerable<IImageRenderPlugin> plugins) => _plugins = plugins.ToList();

    /// <summary>是否有任何可用渲染插件 (false → image-gen 跳过后续环节)。</summary>
    public bool HasRenderer => _plugins.Any(p => p.IsAvailable);

    public IImageRenderPlugin? GetDefault() => _plugins.FirstOrDefault(p => p.IsAvailable);

    public IReadOnlyList<IImageRenderPlugin> All => _plugins;
}
