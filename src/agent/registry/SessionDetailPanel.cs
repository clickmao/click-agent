using System.Text.Json;
using System.Text.Json.Serialization;
using agent.session;

namespace agent.registry;


public sealed class SessionDetailPanel
{
    public string AgentUid { get; set; } = string.Empty;
    public int RequestedIndex { get; set; }
    public bool Found { get; set; }
    public string? Error { get; set; }
    public string? SessionId { get; set; }
    public string? UserId { get; set; }
    public int TurnCount { get; set; }
    public DateTime? CreatedAt { get; set; }
    public DateTime? LastActivityAt { get; set; }
    public string? Memory { get; set; }
    public string? Goal { get; set; }
    public List<MessageEntry> Messages { get; set; } = new();
}
