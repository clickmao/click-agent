using System.Text.Json.Serialization;

namespace agent;


/// <summary>余额条目 (provider 级快照)</summary>
public sealed class BalanceEntryPayload
{
    public string Provider { get; set; } = string.Empty;
    public double? Remaining { get; set; }
    public DateTime At { get; set; }
    public bool FromApi { get; set; }
}
