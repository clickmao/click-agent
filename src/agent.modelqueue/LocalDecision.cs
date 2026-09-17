using System;
using System.Collections.Generic;

namespace agent.modelqueue;


/// <summary>校准结果 (不可变语义: 一旦定档, 上层只做分派)。</summary>
public sealed class LocalDecision
{
    public LocalAction Action { get; set; } = LocalAction.Fatal;

    public string Text { get; set; } = string.Empty;

    public List<ActionToolCall>? ToolCalls { get; set; }

    /// <summary>空正文/失效定因 (复用 R478 机制面, 不新立枚举)。</summary>
    public EmptyBodyCause Cause { get; set; } = EmptyBodyCause.Unknown;

    public bool Retryable { get; set; }

    /// <summary>可见文案 (不含徽标前缀; 由调用方拼 <c>ModelQueueRouter.EmptyBodyBannerPrefix</c>)。</summary>
    public string? Banner { get; set; }

    /// <summary>打点用稳定短名 (禁本地化)。</summary>
    public string Reason { get; set; } = string.Empty;
}
