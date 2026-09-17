using System.Text.Json;
using System.Text.Json.Serialization;
using agent.session;

namespace agent.registry;


public sealed class SessionListPanel
{
    public string AgentUid { get; set; } = string.Empty;
    public int SessionCount { get; set; }
    public List<SessionSummaryEntry> Sessions { get; set; } = new();
}
