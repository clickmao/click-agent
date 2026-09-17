using agent.config;
using agent.registry;

namespace agent.intent;


/// <summary>节点闸门裁决 (不可变, 可审计/可离线重放)。</summary>
public sealed record FormalGateDecision(
    bool Allowed,
    FormalGateDisposition Disposition,
    string ReasonCode,
    string VerdictText,
    string? Counterexample,
    string? AssertText,
    double Ms)
{
    /// <summary>硬约束: 本层纯本地, 任何分支都不产生 LLM 调用。</summary>
    public bool WouldCallLlm => false;
}
