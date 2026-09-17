using System.Text.Json;
using System.Text.Json.Serialization;
using agent.session;

namespace agent.registry;


public sealed class CapabilityEntry
{
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string Source { get; set; } = string.Empty;
}
