using System.Text.Json;
using System.Text.Json.Serialization;
using agent.session;

namespace agent.registry;


// ── 面板 DTO (source-gen JSON, AOT 安全) ──

public sealed class GlobalStatusPanel
{
    public int TurnCount { get; set; }
    public string? LastIntent { get; set; }
    public string? ForecastTendency { get; set; }
    public List<string> PreferenceSummary { get; set; } = new();
    public int SessionCount { get; set; }
    public int AgentCount { get; set; }
    public List<CapabilityEntry> Capabilities { get; set; } = new();

    /// <summary>需求3: 会话中断恢复裁定 (null = 无检查点)</summary>
    public RecoveryPanel? Recovery { get; set; }
}
