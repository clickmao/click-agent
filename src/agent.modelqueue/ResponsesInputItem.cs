using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>
/// R479: Responses 协议**输入项** (typed)。构建后不可变 (值语义), 便于逐字节复现。
/// </summary>
public sealed class ResponsesInputItem
{
    public ResponsesItemKind Kind { get; private init; }

    public string Role { get; private init; } = "user";

    public string Text { get; private init; } = string.Empty;

    public string CallId { get; private init; } = string.Empty;

    public string Output { get; private init; } = string.Empty;

    public static ResponsesInputItem UserText(string text)
        => new() { Kind = ResponsesItemKind.Message, Role = "user", Text = text };

    public static ResponsesInputItem SystemText(string text)
        => new() { Kind = ResponsesItemKind.Message, Role = "system", Text = text };

    public static ResponsesInputItem AssistantText(string text)
        => new() { Kind = ResponsesItemKind.Message, Role = "assistant", Text = text };

    /// <summary>动作环回灌: 工具结果作为独立 typed item (不混进 user 文本)。</summary>
    public static ResponsesInputItem FunctionCallOutput(string callId, string output)
        => new() { Kind = ResponsesItemKind.FunctionCallOutput, CallId = callId ?? string.Empty, Output = output ?? string.Empty };
}
