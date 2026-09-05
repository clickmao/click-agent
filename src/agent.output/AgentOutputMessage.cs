namespace agent.output;

/// <summary>
/// 底层输出模式 (v7.13, 用户钦定): LLM 返回经内部管道处理后有两种呈现模式。
/// 内部管道只流转 AgentOutputMessage (结构化底层格式), 呈现层按 Mode 渲染。
/// </summary>
public enum OutputMode
{
    /// <summary>
    /// Markdown 模式: 全部人性化可读格式 — 标题/列表/粗体/代码围栏/表格,
    /// 文件日志与富界面 (支持 markdown 的通道) 用此模式。
    /// </summary>
    Markdown,

    /// <summary>
    /// 纯文本模式: 去格式化的直接文本 (无围栏/标题符/表格线),
    /// 控制台窄屏/管道/纯终端会话用此模式 — 控制台仍会着色, 只是排版降为平铺。
    /// </summary>
    PlainText,
}

/// <summary>底层消息种类: 一切出口内容 (LLM 结果/问询/日志/审批/错误) 的统一分类</summary>
public enum AgentOutputKind
{
    /// <summary>LLM 最终回答 (经区段管道处理后)</summary>
    Answer,

    /// <summary>问询 (批量澄清/证据补充 — 内部含结构化问题列表)</summary>
    Question,

    /// <summary>执行日志/步骤明细</summary>
    Log,

    /// <summary>敏感操作审批请求</summary>
    Approval,

    /// <summary>错误 (诚实上报, 不伪装成回答)</summary>
    Error,

    /// <summary>状态面板 (/status 等)</summary>
    Status,
}

/// <summary>输出区段: LLM 返回经 ResponseSegmentRouter 标记后的底层单元</summary>
public sealed class AgentOutputSegment
{
    /// <summary>区段类型: text / code / inline-code / question-group / status-table</summary>
    public string Type { get; set; } = "text";

    /// <summary>区段内容 (code 时为代码体)</summary>
    public string Content { get; set; } = string.Empty;

    /// <summary>代码语言 (Type=code 时)</summary>
    public string? Language { get; set; }

    /// <summary>附加元数据 (问题组的 DataType/选项等; JSON 字符串 — AOT 由宿主侧 source-gen 处理)</summary>
    public Dictionary<string, string>? Meta { get; set; }
}

/// <summary>
/// 底层输出消息 (v7.13): 一切返回内容的统一内部格式。
/// LLM 回答 → ResponseSegmentRouter 标记 → 拆成 Segments 填进来;
/// 问询 → ClarificationBatch 构造 Question 消息;
/// 日志 → Log 消息。呈现层 (控制台/文件/UI) 只消费这一种格式, 按需渲染。
/// </summary>
public sealed class AgentOutputMessage
{
    public AgentOutputKind Kind { get; set; } = AgentOutputKind.Answer;

    /// <summary>呈现模式 (markdown / 纯文本)</summary>
    public OutputMode Mode { get; set; } = OutputMode.Markdown;

    /// <summary>完整内容 (Markdown 模式下保留原格式; PlainText 模式下为去格式文本)</summary>
    public string Content { get; set; } = string.Empty;

    /// <summary>结构化区段 (Answer 时由区段路由填充; 其他 Kind 可空 — 用 Content 即可)</summary>
    public List<AgentOutputSegment>? Segments { get; set; }

    /// <summary>时间戳 (UTC ticks — 日志排序)</summary>
    public long Timestamp { get; set; } = DateTime.UtcNow.Ticks;

    /// <summary>来源组件 (如 "LocalLlamaCaller" / "ClarificationBatch" / "CliSession")</summary>
    public string Source { get; set; } = string.Empty;

    /// <summary>
    /// 双模式便捷构造: 同一内容给出两种模式的底层消息 (内容本体一份, 呈现时按需转换)。
    /// Markdown 原文放 Content; PlainText 由 OutputFormatter 降格式。
    /// </summary>
    public static AgentOutputMessage FromLlmAnswer(string markdown, string source, List<AgentOutputSegment>? segments = null) =>
        new()
        {
            Kind = AgentOutputKind.Answer,
            Mode = OutputMode.Markdown,
            Content = markdown,
            Segments = segments,
            Source = source,
        };
}

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
