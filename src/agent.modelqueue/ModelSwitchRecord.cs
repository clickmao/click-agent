using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;


/// <summary>模型切换审计事件 (C.4: 自动切换记录切换事件, /status JSON 可读)</summary>
public sealed class ModelSwitchRecord
{
    public string From { get; set; } = string.Empty;
    public string To { get; set; } = string.Empty;

    /// <summary>切换原因 (consecutive_failures / manual / cost_routing)</summary>
    public string Reason { get; set; } = string.Empty;

    public DateTime At { get; set; } = DateTime.UtcNow;
}
