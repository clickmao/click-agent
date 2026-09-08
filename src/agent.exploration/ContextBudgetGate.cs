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

public sealed class ContextGateConfig
{
    /// <summary>警告阈值 (超过 → 微步骤隔离; 更正2: 未达走常规)</summary>
    public int WarnThreshold { get; set; } = 6000;
    /// <summary>硬阈值 (超过 → 诚实丢弃/拒绝, 不硬跑)</summary>
    public int HardThreshold { get; set; } = 9000;
    /// <summary>预期输出 token (est = prompt + 预期输出; 默认 512)</summary>
    public int ExpectedOutputTokens { get; set; } = 512;
    /// <summary>边界防抖带宽 (±5% 内维持上次决策 — MS-F04)</summary>
    public double HysteresisRatio { get; set; } = 0.05;
}

public sealed class ContextGateVerdict
{
    public ContextGateMode Mode { get; set; }
    public int EstimatedTokens { get; set; }
    public int WarnThreshold { get; set; }
    public int HardThreshold { get; set; }
    public string Reason { get; set; } = string.Empty;
}

public sealed class ContextBudgetGate
{
    private readonly ContextGateConfig _config;
    private ContextGateMode _lastMode = ContextGateMode.Normal;
    private int _decidedCount;
    private readonly object _lock = new();

    public ContextBudgetGate(ContextGateConfig? config = null) => _config = config ?? new ContextGateConfig();

    /// <summary>
    /// 判定。promptTokens = 当前 prompt 实测 (prompt_total_tokens 打点同源)。
    /// 防抖: 与上次决策同模式且 est 在阈值 ±5% 内 → 维持 (MS-F04 边界抖动防线)。
    /// </summary>
    public ContextGateVerdict Evaluate(int promptTokens)
    {
        var est = promptTokens + _config.ExpectedOutputTokens;
        var v = new ContextGateVerdict
        {
            EstimatedTokens = est,
            WarnThreshold = _config.WarnThreshold,
            HardThreshold = _config.HardThreshold,
        };
        lock (_lock)
        {
            if (est >= _config.HardThreshold)
            {
                v.Mode = ContextGateMode.HardDrop;
                v.Reason = $"est {est} ≥ hard { _config.HardThreshold} (诚实丢弃策略)";
            }
            else if (est >= _config.WarnThreshold)
            {
                v.Mode = ContextGateMode.IsolatedMicro;
                v.Reason = $"est {est} ≥ warn {_config.WarnThreshold}";
            }
            else
            {
                v.Mode = ContextGateMode.Normal;
                v.Reason = $"est {est} < warn {_config.WarnThreshold} (更正2: 常规方案)";
            }
            // 防抖 (仅 Normal/IsolatedMicro 之间; HardDrop 永不防抖)。
            // A3 教训 (python 复现抓 bug): 首次跨越阈值必须放行 — 防抖只在模式已稳定 (_decidedCount≥2)
            // 后防止边界来回抖动; 否则首次 micro 被"维持上次 Normal"弹回, 门永远打不开。
            var band = _config.WarnThreshold * _config.HysteresisRatio;
            _decidedCount++;
            if (_decidedCount > 2 && v.Mode != _lastMode &&
                v.Mode != ContextGateMode.HardDrop && _lastMode != ContextGateMode.HardDrop)
            {
                var nearBoundary = Math.Abs(est - _config.WarnThreshold) <= band;
                if (nearBoundary)
                {
                    (v.Mode, v.Reason) = (_lastMode, v.Reason + " [hysteresis: 维持上次决策]");
                }
            }
            _lastMode = v.Mode;
        }
        return v;
    }
}
