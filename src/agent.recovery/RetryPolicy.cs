using Microsoft.Extensions.Logging;

namespace agent.recovery;


/// <summary>
/// 重试策略配置
/// </summary>
public class RetryPolicy
{
    public int MaxAttempts { get; set; } = 3;
    public TimeSpan InitialDelay { get; set; } = TimeSpan.FromSeconds(1);
    public TimeSpan MaxDelay { get; set; } = TimeSpan.FromMinutes(1);
    public double BackoffMultiplier { get; set; } = 2.0;
    public bool ExponentialBackoff { get; set; } = true;
    public Func<Exception, bool>? ShouldRetry { get; set; }
}
