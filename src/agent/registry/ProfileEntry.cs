using System.Text.Json;
using System.Text.Json.Serialization;
using agent.session;

namespace agent.registry;


public sealed class ProfileEntry
{
    public string DecisionStyle { get; set; } = string.Empty;
    public string OutputStyle { get; set; } = string.Empty;
    public int MaxRetries { get; set; }
    public bool PreferClarifyFirst { get; set; }
    public Dictionary<string, int> TaskSuccess { get; set; } = new();
    public Dictionary<string, int> TaskFailure { get; set; } = new();
    public Dictionary<string, int> ToolAffinity { get; set; } = new();
}
