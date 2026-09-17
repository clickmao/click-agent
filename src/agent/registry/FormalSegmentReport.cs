using agent.config;
using agent.intent;

namespace agent.registry;


/// <summary>一条区段级形式化裁决 (不可变, 供上层审计/回灌)。</summary>
public sealed record FormalSegmentReport(
    string Verdict,
    string ReasonCode,
    bool Allowed,
    string? Counterexample,
    int ContractChars);
