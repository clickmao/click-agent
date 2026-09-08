using System.Text;

namespace agent.modelqueue;

/// <summary>
/// v0.12.0 B2 (用户钦定 R210) — 图像渲染插件契约。
/// 收敛环: LLM DSL → IImageRenderPlugin.Render → 文件 → 校验。
/// 插件可替换: 默认 SkiaSharp (PNG); SVG 文本实现恒可用 (零依赖兜底)。
/// 边缘选项: 构建时 -p:DisableSkiaRenderer=true 停编 SkiaSharp 插件 (AOT 体积/依赖收缩)。
/// 运行时无可用插件 → image-gen 流程跳过后续环节 (诚实不可用, 不降级硬跑)。
/// </summary>
public interface IImageRenderPlugin
{
    /// <summary>插件名 (打点/日志)</summary>
    string Name { get; }

    /// <summary>产物扩展名 (png/svg)</summary>
    string OutputExtension { get; }

    /// <summary>是否可用 (SkiaSharp: native 资产存在; SVG: 恒 true)</summary>
    bool IsAvailable { get; }

    /// <summary>渲染 DSL shapes → 文件。失败不抛异常, 结果对象携带 Error。</summary>
    ImageRenderResult Render(IReadOnlyList<LocalSvgRenderer.Shape> shapes, int width, int height, string savePath, CancellationToken ct = default);
}

public sealed class ImageRenderResult
{
    public bool Ok { get; set; }
    public string? Path { get; set; }
    public long FileBytes { get; set; }
    public string? Error { get; set; }
    public int WallMs { get; set; }
}

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
