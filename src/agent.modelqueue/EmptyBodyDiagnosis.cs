namespace agent.modelqueue;

/// <summary>
/// R478: 空正文**定因** (机制面) —— 判据只取上游协议字段 (`finish_reason` / `tool_calls`),
/// 不取用户文本关键词, 也不猜测成因。
/// 依据: R477 真机 20/20 空正文调用的上游 `finish_reason == tool_calls`、
/// `max_tokens == None` (未被截断)、`reasoning_tokens_max` 仅 395/122 ≪ 预算 ⇒
/// 旧文案「推理过程占满了输出预算」是**误诊**, 且据此白跑一次 32k 预算重试 (调用数 + token 双浪费)。
/// </summary>
public enum EmptyBodyCause
{
    /// <summary>上游请求执行工具动作 (finish_reason=tool_calls 或 tool_calls 非空)。重试不可能产出正文。</summary>
    ToolCall,

    /// <summary>输出预算耗尽 (finish_reason=length; 或未报原因但确有推理内容 = 推理吃满预算)。</summary>
    LengthExhausted,

    /// <summary>上游以 stop 正常收尾但正文为空。</summary>
    UpstreamStop,

    /// <summary>其它/未知 finish_reason。</summary>
    Unknown,
}

/// <summary>R478: 空正文定因 + 可见文案单源 (AOT 安全: 纯静态, 零反射)。</summary>
public static class EmptyBodyDiagnosis
{
    public const string ReasonToolCalls = "tool_calls";
    public const string ReasonLength = "length";
    public const string ReasonStop = "stop";

    /// <summary>
    /// 分类 (纯函数, 可单测)。规则组 (顺序即优先级):
    /// ① tool_calls 计数 > 0 ∨ finish_reason == "tool_calls" ⇒ <see cref="EmptyBodyCause.ToolCall"/>;
    /// ② finish_reason == "length" ⇒ <see cref="EmptyBodyCause.LengthExhausted"/>;
    /// ③ finish_reason 为空/空白 ∧ reasoningChars > 0 ⇒ <see cref="EmptyBodyCause.LengthExhausted"/>
    ///    (上游未报原因但确有推理 ⇒ 与 length 同一失效面: 推理吃满输出预算);
    /// ④ finish_reason == "stop" ⇒ <see cref="EmptyBodyCause.UpstreamStop"/>;
    /// ⑤ 其余非空 ⇒ <see cref="EmptyBodyCause.Unknown"/>。
    /// </summary>
    public static EmptyBodyCause Classify(string? finishReason, int toolCalls, int reasoningChars)
    {
        if (toolCalls > 0) return EmptyBodyCause.ToolCall;
        var fr = (finishReason ?? string.Empty).Trim();
        if (fr.Equals(ReasonToolCalls, StringComparison.OrdinalIgnoreCase)) return EmptyBodyCause.ToolCall;
        if (fr.Equals(ReasonLength, StringComparison.OrdinalIgnoreCase)) return EmptyBodyCause.LengthExhausted;
        if (fr.Length == 0) return reasoningChars > 0 ? EmptyBodyCause.LengthExhausted : EmptyBodyCause.Unknown;
        if (fr.Equals(ReasonStop, StringComparison.OrdinalIgnoreCase)) return EmptyBodyCause.UpstreamStop;
        return EmptyBodyCause.Unknown;
    }

    /// <summary>是否值得「升预算 + 抑制推理」重试一次。<see cref="EmptyBodyCause.ToolCall"/> ⇒ 否 (协议级请求, 重试必空)。</summary>
    public static bool Retryable(EmptyBodyCause cause) => cause != EmptyBodyCause.ToolCall;

    /// <summary>打点用稳定短名 (禁本地化, 禁自由文本)。</summary>
    public static string CauseName(EmptyBodyCause cause) => cause switch
    {
        EmptyBodyCause.ToolCall => "tool_call",
        EmptyBodyCause.LengthExhausted => "length_exhausted",
        EmptyBodyCause.UpstreamStop => "upstream_stop",
        _ => "unknown",
    };

    /// <summary>
    /// 面向用户的降级文案 (徽标前缀**不含**在返回值内, 由调用方拼 <see cref="ModelQueueRouter.EmptyBodyBannerPrefix"/>)。
    /// 铁律: 文案必须**带上游真实 finish_reason**, 禁再断言未取证的成因 (R477 误诊教训)。
    /// </summary>
    public static string Banner(EmptyBodyCause cause, string? finishReason)
    {
        var fr = string.IsNullOrWhiteSpace(finishReason) ? "(未上报)" : finishReason!.Trim();
        return cause switch
        {
            EmptyBodyCause.ToolCall => ": 上游请求执行工具动作 (finish_reason=" + fr + ") — 当前链路未启用工具执行。"
                + "请重试, 或改用不带工具的模型。",
            EmptyBodyCause.LengthExhausted => ": 输出预算被推理占满 (finish_reason=" + fr
                + ", 已自动放宽输出预算并重试一次仍失败)。请重试, 或改用非推理模型 / 缩小任务范围。",
            EmptyBodyCause.UpstreamStop => ": 上游以 finish_reason=" + fr + " 结束但未给出正文。请重试或切换模型。",
            _ => ": 上游 finish_reason=" + fr + " 未给出可用正文。请重试或切换模型。",
        };
    }

    /// <summary>动作环可接管 (工具执行面已启用 ∧ 上游确实给了 tool_calls) ⇒ 不上徽标, 保留 tool_calls 上抛。</summary>
    public static bool RoutableToActionLoop(EmptyBodyCause cause, int toolCalls, bool actionLoopEnabled)
        => cause == EmptyBodyCause.ToolCall && toolCalls > 0 && actionLoopEnabled;
}
