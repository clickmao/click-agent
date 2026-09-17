using System.Text.Json;

namespace agent.exploration;


/// <summary>
/// v0.13.3 M2 (用户钦定 Baseline 换血) — 上下文预算门:
/// 每步骤执行前估算 est_tokens (当前 prompt + 预期输出), 与 WARN/HARD 阈值比较;
/// est &lt; WARN → normal (更正2: 现状零改动); WARN ≤ est &lt; HARD → isolated_micro;
/// est ≥ HARD → hard_drop (诚实丢弃/拒绝策略, 不硬跑)。
/// 打点 context_gate (est_tokens, threshold, mode) — 微步骤隔离触发的前置观测点。
/// </summary>
public enum ContextGateMode
{
    Normal = 0,
    IsolatedMicro = 1,
    HardDrop = 2,
}
