using System.Collections.Generic;
using System.Text;

namespace agent.r1;

/// <summary>
/// 补充块渲染（**尾部可变区**）。长任务节点提示 / 任何在既有常量前缀之后追加的 prompt 都用它。
///
/// 纪律：只在**尾部**追加 —— 公共前缀（preamble、全计划等跨节点相同的部分）字节不变，
/// 因此 llama-server 的前缀缓存（CachePrompt）复用不受影响；恒前缀 ≥97% 口径不破。
///
/// 无补充（null / 空 / 全空白）⇒ 返回空串，提示逐字节等于注入前的版本（零行为变化）。
/// </summary>
public static class SupplementBlock
{
    /// <summary>块头（机检锚点：出现即证明该提示被注入过用户补充）。</summary>
    public const string Header = "【用户补充】";

    /// <summary>尾部尾注（固定文本，便于机检与人工识别）。</summary>
    public const string Footer = "(以上为用户在任务运行中补充的信息：与当前步骤相关才执行，无关请忽略。)";

    /// <summary>渲染补充块；无可渲染内容时返回空串。</summary>
    public static string Render(IReadOnlyList<string>? supplements)
    {
        if (supplements is null || supplements.Count == 0)
        {
            return string.Empty;
        }

        var lines = new List<string>(supplements.Count);
        for (var i = 0; i < supplements.Count; i++)
        {
            var text = supplements[i];
            if (string.IsNullOrWhiteSpace(text))
            {
                continue;
            }

            lines.Add(text.Trim());
        }

        if (lines.Count == 0)
        {
            return string.Empty;
        }

        var sb = new StringBuilder(128 + (lines.Count * 64));
        sb.Append('\n').Append('\n').Append(Header).Append('\n');
        for (var i = 0; i < lines.Count; i++)
        {
            sb.Append("- ").Append(lines[i]).Append('\n');
        }

        sb.Append(Footer).Append('\n');
        return sb.ToString();
    }
}
