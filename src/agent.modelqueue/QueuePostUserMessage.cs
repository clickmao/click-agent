using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>回灌消息 (追加在 user 之后, 保缓存前缀不变)。</summary>
public sealed class QueuePostUserMessage
{
    public string Role { get; set; } = "assistant";
    public string Content { get; set; } = string.Empty;
    /// <summary>assistant 消息的 tool_calls (role=assistant 时非空)。</summary>
    public List<ActionToolCall>? ToolCalls { get; set; }
    /// <summary>tool 消息对应的 id (role=tool 时非空)。</summary>
    public string? ToolCallId { get; set; }

    public static QueuePostUserMessage AssistantToolCalls(List<ActionToolCall> calls)
        => new() { Role = "assistant", Content = string.Empty, ToolCalls = calls };

    public static QueuePostUserMessage ToolResult(string id, string content)
        => new() { Role = "tool", Content = content, ToolCallId = id };
}
