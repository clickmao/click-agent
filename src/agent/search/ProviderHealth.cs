using System.Text.Json.Serialization;

namespace agent.search;


/// <summary>
/// 搜索源健康状态 (熔断器状态机: Closed → Open → HalfOpen)
/// </summary>
public class ProviderHealth
{
    /// <summary>连续失败次数</summary>
    public int ConsecutiveFailures { get; set; }

    /// <summary>累计成功次数</summary>
    public long TotalSuccess { get; set; }

    /// <summary>累计失败次数</summary>
    public long TotalFailures { get; set; }

    /// <summary>最近一次成功时间 (UTC)</summary>
    public DateTime? LastSuccessAt { get; set; }

    /// <summary>最近一次失败时间 (UTC)</summary>
    public DateTime? LastFailureAt { get; set; }

    /// <summary>熔断打开时间 (UTC)。非空且未过冷却期 = Open 状态</summary>
    public DateTime? OpenedAt { get; set; }

    /// <summary>是否处于熔断打开状态 (含冷却期判断)</summary>
    [JsonIgnore]
    public bool IsCircuitOpen => OpenedAt.HasValue &&
        DateTime.UtcNow - OpenedAt.Value < CircuitCooldown;

    /// <summary>熔断冷却期, 过后半开试通, 成功则闭合</summary>
    [JsonIgnore]
    public static TimeSpan CircuitCooldown => TimeSpan.FromMinutes(2);

    /// <summary>记录一次成功 (闭合熔断)</summary>
    public void RecordSuccess()
    {
        ConsecutiveFailures = 0;
        TotalSuccess++;
        LastSuccessAt = DateTime.UtcNow;
        OpenedAt = null;
    }

    /// <summary>记录一次失败 (达到阈值则打开熔断)</summary>
    public void RecordFailure(int openThreshold)
    {
        ConsecutiveFailures++;
        TotalFailures++;
        LastFailureAt = DateTime.UtcNow;
        if (ConsecutiveFailures >= openThreshold)
            OpenedAt ??= DateTime.UtcNow;
    }
}
