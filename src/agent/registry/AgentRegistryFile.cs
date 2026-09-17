using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.registry;


/// <summary>registry.json 持久化模型</summary>
public class AgentRegistryFile
{
    public List<AgentIdentity> Agents { get; set; } = new();
}
