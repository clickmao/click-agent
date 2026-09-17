using agent.registry;

namespace agent.registry;


/// <summary>
/// 代码审查插件 (内置示例): 非 UI 代码段路由到审查钩子。
/// 真实审查服务由宿主注入 (Func 委托), 插件只负责路由与降级 — 无服务时原样透传。
/// </summary>
public sealed class CodeReviewPlugin : IResponseSegmentPlugin
{
    private readonly Func<ResponseSegment, CancellationToken, Task<string?>>? _reviewHook;

    public CodeReviewPlugin(Func<ResponseSegment, CancellationToken, Task<string?>>? reviewHook = null)
    {
        _reviewHook = reviewHook;
    }

    public string Name => "code-review";

    public IReadOnlySet<SegmentKind> Consumes { get; } =
        new HashSet<SegmentKind> { SegmentKind.Code };

    public async Task<string> HandleAsync(ResponseSegment segment, CancellationToken ct = default)
    {
        if (UiCapturePlugin.IsUiAsset(segment))
            return segment.Content; // UI 资产不进审查

        if (_reviewHook == null)
            return segment.Content; // 未配置审查服务 → 原样透传 (零损耗降级)

        var reviewed = await _reviewHook(segment, ct);
        return reviewed ?? segment.Content;
    }
}
