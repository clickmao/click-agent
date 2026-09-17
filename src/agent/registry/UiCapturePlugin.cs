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
