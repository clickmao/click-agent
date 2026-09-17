namespace agent.output;


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
