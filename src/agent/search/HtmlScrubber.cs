using System.Text.Json;
using Microsoft.Extensions.Logging;
using agent.core;

namespace agent.search;


/// <summary>
/// HTML 清洗的 source-gen 正则 (Native AOT: 编译期生成扫描器, 零运行时反射编译)。
/// </summary>
internal static partial class HtmlScrubber
{
    [System.Text.RegularExpressions.GeneratedRegex(
        "<(script|style)[^>]*>.*?</\\1>",
        System.Text.RegularExpressions.RegexOptions.Singleline |
        System.Text.RegularExpressions.RegexOptions.IgnoreCase)]
    internal static partial System.Text.RegularExpressions.Regex StripScriptStyle();

    [System.Text.RegularExpressions.GeneratedRegex("<[^>]+>")]
    internal static partial System.Text.RegularExpressions.Regex StripTags();

    [System.Text.RegularExpressions.GeneratedRegex("\\s+")]
    internal static partial System.Text.RegularExpressions.Regex CollapseWhitespace();
}
