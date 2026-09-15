using System;
using System.Collections.Generic;

namespace agent.modelqueue;

/// <summary>
/// R479: **本地该做什么** (精准语义) —— 由上游返回校准出的动作类别。
/// 这是「LLM 返回 → 本地动作」的标准化出口; 本地 LLM 与远端 LLM **同用这一个函数**
/// (协议同形 ⇒ 语义同一), 不为本地另立一套判据。
/// </summary>
public enum LocalAction
{
    /// <summary>直接交付正文。</summary>
    Answer,

    /// <summary>执行工具调用 (声明面白名单内) 并回灌。</summary>
    RunTools,

    /// <summary>同一请求值得重发 (输出预算类失效)。</summary>
    Retry,

    /// <summary>不可用但可解释: 必须给用户可见文案, 禁静默空回复。</summary>
    VisibleFailure,

    /// <summary>传输/解析失败: 上层按通道失败处理 (不计入上游判据)。</summary>
    Fatal,
}

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

/// <summary>
/// R479: Responses 协议返回 → 本地动作的**单一校准函数**。
/// 判据**只取协议字段** (Failure / status / incomplete_details.reason / output 项类型 / 工具调用计数),
/// 不取用户文本关键词, 不猜成因 (承 R478 铁律)。
/// 文案**单源**: 一切失效文案都经 <see cref="EmptyBodyDiagnosis.Banner"/>, 本类不新写第二处文案实现。
/// </summary>
public static class LocalDecisionMap
{
    public const string StatusCompleted = "completed";
    public const string StatusIncomplete = "incomplete";
    public const string StatusFailed = "failed";
    public const string ReasonMaxOutput = "max_output_tokens";
    public const string FinishToolCalls = "tool_calls";
    public const string FinishLength = "length";
    public const string FinishStop = "stop";

    /// <summary>
    /// 规则 (顺序即优先级):
    /// ① 解析/传输失败 ⇒ <see cref="LocalAction.Fatal"/> (上层按通道失败; 文案取上报告警);
    /// ② 工具调用计数 &gt; 0 ⇒ 动作环开: <see cref="LocalAction.RunTools"/>; 关: 可见失败 (cause=ToolCall, 禁重试);
    /// ③ status=completed ∧ 正文非空 ⇒ <see cref="LocalAction.Answer"/>;
    /// ④ status=incomplete ∧ reason=max_output_tokens ⇒ <see cref="LocalAction.Retry"/> (cause=LengthExhausted);
    /// ⑤ status=completed ∧ 正文空 ⇒ 可见失败 (cause=UpstreamStop);
    /// ⑥ 其余 (未知状态/未知原因) ⇒ 可见失败 (cause=Unknown) —— fail-closed, 禁猜。
    /// </summary>
    public static LocalDecision FromResponses(ResponsesResult r, bool actionLoopEnabled)
    {
        if (r.Failure != null)
        {
            return new LocalDecision
            {
                Action = LocalAction.Fatal,
                Cause = EmptyBodyCause.Unknown,
                Retryable = false,
                Reason = "protocol_failure",
                Banner = EmptyBodyDiagnosis.Banner(EmptyBodyCause.Unknown, ProtocolReason(r)),
            };
        }

        if (r.ToolCalls.Count > 0)
        {
            if (actionLoopEnabled)
            {
                return new LocalDecision
                {
                    Action = LocalAction.RunTools,
                    ToolCalls = r.ToolCalls,
                    Text = r.Text,
                    Cause = EmptyBodyCause.ToolCall,
                    Retryable = false,
                    Reason = "run_tools",
                };
            }

            return Visible(r, EmptyBodyCause.ToolCall, "tool_calls_without_action_loop");
        }

        if (IsStatus(r, StatusCompleted) && r.HasText)
        {
            return new LocalDecision
            {
                Action = LocalAction.Answer,
                Text = r.Text,
                Cause = EmptyBodyCause.Unknown,
                Retryable = false,
                Reason = "answer",
            };
        }

        if (IsStatus(r, StatusIncomplete) && string.Equals(r.IncompleteReason, ReasonMaxOutput, StringComparison.OrdinalIgnoreCase))
            return RetryDecision(r, EmptyBodyCause.LengthExhausted, "max_output_tokens");

        if (IsStatus(r, StatusIncomplete))
            return Visible(r, EmptyBodyCause.Unknown, "incomplete_other");

        if (IsStatus(r, StatusFailed)) return Visible(r, EmptyBodyCause.Unknown, "upstream_failed");

        if (IsStatus(r, StatusCompleted)) return Visible(r, EmptyBodyCause.UpstreamStop, "completed_empty");

        return Visible(r, EmptyBodyCause.Unknown, "status_unrecognized");
    }

    /// <summary>传输层失败 (连接/超时/HTTP 非 2xx): 不计入上游判据, 由通道失败面处理。</summary>
    public static LocalDecision FromTransportFailure(string errorKind)
        => new()
        {
            Action = LocalAction.Fatal,
            Cause = EmptyBodyCause.Unknown,
            Retryable = true,
            Reason = "transport_failure",
            Banner = EmptyBodyDiagnosis.Banner(EmptyBodyCause.Unknown, errorKind),
        };

    private static LocalDecision Visible(ResponsesResult r, EmptyBodyCause cause, string reason) => new()
    {
        Action = LocalAction.VisibleFailure,
        Text = r.Text,
        Cause = cause,
        Retryable = EmptyBodyDiagnosis.Retryable(cause),
        Reason = reason,
        Banner = EmptyBodyDiagnosis.Banner(cause, ProtocolReason(r, cause)),
    };

    private static LocalDecision RetryDecision(ResponsesResult r, EmptyBodyCause cause, string reason) => new()
    {
        Action = LocalAction.Retry,
        Text = r.Text,
        Cause = cause,
        Retryable = EmptyBodyDiagnosis.Retryable(cause),
        Reason = reason,
        Banner = EmptyBodyDiagnosis.Banner(cause, ProtocolReason(r, cause)),
    };

    private static bool IsStatus(ResponsesResult r, string status)
        => string.Equals(r.Status, status, StringComparison.OrdinalIgnoreCase);

    /// <summary>协议字段 → 文案所需的原因串 (与 chat 侧 finish_reason 词表对齐; 无则回退协议原文)。</summary>
    internal static string ProtocolReason(ResponsesResult r, EmptyBodyCause cause)
    {
        if (cause == EmptyBodyCause.ToolCall) return FinishToolCalls;
        if (cause == EmptyBodyCause.LengthExhausted) return FinishLength;
        if (cause == EmptyBodyCause.UpstreamStop) return FinishStop;
        if (r.IncompleteReason.Length > 0) return r.IncompleteReason;
        return r.Status;
    }

    internal static string ProtocolReason(ResponsesResult r) => ProtocolReason(r, EmptyBodyCause.Unknown);
}
