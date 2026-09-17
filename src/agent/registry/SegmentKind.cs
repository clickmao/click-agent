using System.Text.RegularExpressions;

namespace agent.registry;

/// <summary>返回内容区段类型</summary>
public enum SegmentKind
{
    /// <summary>普通文本</summary>
    PlainText,

    /// <summary>fenced 代码块 (```lang ... ```), Language=语言标识</summary>
    Code,

    /// <summary>行内代码 (单反引号)</summary>
    InlineCode,
}
