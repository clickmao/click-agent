using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>Responses 响应解析结果 (协议字段面; <see cref="Failure"/> 非空 ⇒ 不可用, fail-closed)。</summary>
public sealed class ResponsesResult
{
    public string Id { get; set; } = string.Empty;

    public string Status { get; set; } = string.Empty;

    /// <summary>incomplete_details.reason (如 max_output_tokens)。</summary>
    public string IncompleteReason { get; set; } = string.Empty;

    public string Text { get; set; } = string.Empty;

    public string ReasoningText { get; set; } = string.Empty;

    public List<ResponsesOutputItem> Items { get; } = new();

    public List<ActionToolCall> ToolCalls { get; } = new();

    public ResponsesUsage Usage { get; set; } = new();

    /// <summary>未知 item 计数 (不静默丢弃; 全未知 ⇒ fail-closed)。</summary>
    public int UnknownItems { get; set; }

    public string? Failure { get; set; }

    public bool HasText => Text.Length > 0;
}
