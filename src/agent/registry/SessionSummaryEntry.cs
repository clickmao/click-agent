using System.Text.Json;
using System.Text.Json.Serialization;
using agent.session;

namespace agent.registry;


public sealed class SessionSummaryEntry
{
    public int Index { get; set; }
    public string SessionId { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public int TurnCount { get; set; }
    public int MessageCount { get; set; }
    public DateTime LastActivityAt { get; set; }
    public string Preview { get; set; } = string.Empty;
}
