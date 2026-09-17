using System.Text.Json;

namespace agent.exploration;


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
