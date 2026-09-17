namespace agent.registry;


/// <summary>契约判定结果。不可变; 便于审计落盘与离线重放。</summary>
public sealed record FormalContractResult(
    FormalContractDecision Decision,
    string ReasonCode,
    string? AssertionText = null,
    string? Declaration = null)
{
    /// <summary>可放行(仅"不提供断言"这一种情形)。</summary>
    public bool IsPassable => Decision == FormalContractDecision.NoFormal;

    /// <summary>须交本地内核裁决(仅 Assertion)。</summary>
    public bool NeedsKernel => Decision == FormalContractDecision.Assertion;

    /// <summary>硬约束: 契约层永不触发 LLM 追问/重试。恒 false。</summary>
    public bool RequiresLlmRetry => false;
}
