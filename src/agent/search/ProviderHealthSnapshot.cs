using System.Text.Json.Serialization;

namespace agent.search;


/// <summary>
/// 健康状态的持久化快照 (运行时 ProviderHealth 的磁盘形态)
/// </summary>
public class ProviderHealthSnapshot
{
    public long TotalSuccess { get; set; }
    public long TotalFailures { get; set; }
    public DateTime? LastSuccessAt { get; set; }
    public DateTime? LastFailureAt { get; set; }

    public static ProviderHealthSnapshot From(ProviderHealth h) => new()
    {
        TotalSuccess = h.TotalSuccess,
        TotalFailures = h.TotalFailures,
        LastSuccessAt = h.LastSuccessAt,
        LastFailureAt = h.LastFailureAt,
    };
}
