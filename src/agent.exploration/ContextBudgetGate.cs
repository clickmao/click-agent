using System.Text.Json;

namespace agent.exploration;

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
