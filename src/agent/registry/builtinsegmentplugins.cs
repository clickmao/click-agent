using agent.registry;

namespace agent.registry;

/// <summary>
/// UI 捕获插件 (内置示例): html/svg 段标记为 UI 可用区段。
/// 消费方式: 追加定位注释, 外部 UI 按 ResponseSegment 日志/审计直接取区段坐标。
/// </summary>
public sealed class UiCapturePlugin : IResponseSegmentPlugin
{
    public string Name => "ui-capture";

    public IReadOnlySet<SegmentKind> Consumes { get; } =
        new HashSet<SegmentKind> { SegmentKind.Code };

    public Task<string> HandleAsync(ResponseSegment segment, CancellationToken ct = default)
    {
        var lang = segment.Language?.ToLowerInvariant();
        if (lang is "html" or "svg" or "xml")
        {
            // 不改内容 — 只在审计语境可读 (此处恒等返回; UI 端通过 StartIndex/Length 定位)
            return Task.FromResult(segment.Content);
        }
        return Task.FromResult(segment.Content);
    }

    /// <summary>该段是否属于 UI 资产 (供宿主/审计快速判定)</summary>
    public static bool IsUiAsset(ResponseSegment segment) =>
        segment.Kind == SegmentKind.Code &&
        segment.Language?.ToLowerInvariant() is "html" or "svg" or "xml";
}

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
