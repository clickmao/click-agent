namespace agent.output;

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
