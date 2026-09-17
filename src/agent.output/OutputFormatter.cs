namespace agent.output;


/// <summary>
/// 输出格式化器 (v7.13): Markdown ⇄ 纯文本 的双向转换 (纯规则, 无 IO)。
/// </summary>
public static class OutputFormatter
{
    /// <summary>markdown → 纯文本 (去围栏/标题符/粗斜体标记/表格线, 保内容与换行结构)</summary>
    public static string ToPlainText(string markdown)
    {
        if (string.IsNullOrEmpty(markdown))
            return string.Empty;

        var lines = markdown.Replace("\r\n", "\n").Split('\n');
        var outLines = new List<string>(lines.Length);
        var inFence = false;

        foreach (var raw in lines)
        {
            var line = raw;

            // 围栏: 保留代码体, 去 ``` 行
            if (line.TrimStart().StartsWith("```"))
            {
                inFence = !inFence;
                continue;
            }
            if (inFence)
            {
                outLines.Add(line);
                continue;
            }

            // 标题符 → 纯文本标题行
            var trimmed = line.TrimStart();
            if (trimmed.StartsWith('#'))
                line = trimmed.TrimStart('#').Trim();
            // 粗体/斜体标记
            line = line.Replace("**", "").Replace("__", "");
            // 行内代码反引号
            line = StripInlineCode(line);
            // 列表符 → 圆点
            if (trimmed.StartsWith("- ") || trimmed.StartsWith("* "))
                line = "· " + trimmed[2..];
            // 表格线行 (|---|---|) 直接丢弃
            if (System.Text.RegularExpressions.Regex.IsMatch(line, @"^\s*\|?[\s:|-]+\|?\s*$") && line.Contains('|'))
                continue;

            outLines.Add(line);
        }

        return string.Join('\n', outLines);
    }

    /// <summary>纯文本 → markdown (内容已是平铺文本, 只补最小结构: 非空行分段)</summary>
    public static string ToMarkdown(string plainText)
    {
        if (string.IsNullOrEmpty(plainText))
            return string.Empty;
        return plainText.Replace("\r\n", "\n");
    }

    private static string StripInlineCode(string line)
    {
        var sb = new System.Text.StringBuilder(line.Length);
        var inCode = false;
        foreach (var ch in line)
        {
            if (ch == '`')
            {
                inCode = !inCode;
                continue;
            }
            sb.Append(ch);
        }
        return sb.ToString();
    }
}
