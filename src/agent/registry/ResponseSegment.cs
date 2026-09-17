using System.Text.RegularExpressions;

namespace agent.registry;


/// <summary>
/// LLM 返回内容的一段 — 快速标记的产物。
/// StartIndex/Length 指向原始文本, 供 UI 高亮/其他流程按区段取用, 无需复制字符串。
/// </summary>
public class ResponseSegment
{
    public SegmentKind Kind { get; init; }

    /// <summary>区段内容 (代码段不含围栏)</summary>
    public string Content { get; init; } = string.Empty;

    /// <summary>在原始全文中的偏移 (UI 定位用)</summary>
    public int StartIndex { get; init; }

    public int Length { get; init; }

    /// <summary>代码语言 (```html → "html")</summary>
    public string? Language { get; init; }

    /// <summary>R371 D4-b: 是否由**启发式提升**而来 (无围栏) — 供真机 KPI 归因 (fenced vs heuristic)。</summary>
    public bool Promoted { get; set; }

    /// <summary>路由到的插件名 (诊断/审计)</summary>
    public string? RoutedTo { get; set; }
}
