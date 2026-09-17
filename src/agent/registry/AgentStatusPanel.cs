using System.Text.Json;
using System.Text.Json.Serialization;
using agent.session;

namespace agent.registry;


public sealed class AgentStatusPanel
{
    public string AgentUid { get; set; } = string.Empty;
    public bool Exists { get; set; }
    public int ContextChars { get; set; }
    public int SessionCount { get; set; }
    public ProfileEntry Profile { get; set; } = new();
    public string LongTermMemory { get; set; } = string.Empty;
    public int MemoryMaxChars { get; set; }
    public GoalEntry? Goal { get; set; }
}
