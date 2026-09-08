
namespace agent.contextgradient;

/// <summary>
/// v0.13.3 D4 (标准工业模式 M4 熔断器): 连续 N 次压缩失败 (异常/哨兵丢失超限) → 熔断
/// (直通原文, 不再尝试压缩) open 持续 coolDownMs; 半开 (half-open) 放行 1 条试压缩,
/// 成功 → closed, 失败 → 重新 open。防系统性失灵时反复硬跑。
/// </summary>
public sealed class CompressionBreaker
{
    private readonly int _failureThreshold;
    private readonly int _coolDownMs;
    private readonly object _lock = new();
    private int _consecutiveFailures;
    private long _openUntilMs; // Environment.TickCount64 基
    private bool _halfOpenTrial;

    public CompressionBreaker(int failureThreshold = 5, int coolDownMs = 60_000)
    {
        _failureThreshold = failureThreshold;
        _coolDownMs = coolDownMs;
    }

    /// <summary>当前是否允许尝试压缩 (closed 或 half-open 试探)。</summary>
    public bool AllowAttempt
    {
        get
        {
            lock (_lock)
            {
                if (_consecutiveFailures < _failureThreshold) return true; // closed
                var now = Environment.TickCount64;
                if (now >= _openUntilMs)
                {
                    if (!_halfOpenTrial)
                    {
                        _halfOpenTrial = true; // 半开放行一条试探
                        return true;
                    }
                    return false; // 试探已在途, 其余继续拒绝
                }
                return false; // open 冷却中
            }
        }
    }

    /// <summary>记录一次结果: 失败累计, 成功复位。</summary>
    public void Record(bool success)
    {
        lock (_lock)
        {
            if (success)
            {
                _consecutiveFailures = 0;
                _halfOpenTrial = false;
                _openUntilMs = 0;
            }
            else
            {
                _consecutiveFailures++;
                if (_consecutiveFailures >= _failureThreshold)
                {
                    _openUntilMs = Environment.TickCount64 + _coolDownMs;
                    _halfOpenTrial = false;
                }
            }
        }
    }
}
