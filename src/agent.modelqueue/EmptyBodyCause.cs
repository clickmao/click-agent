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
