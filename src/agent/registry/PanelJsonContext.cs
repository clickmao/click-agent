using System.Text.Json;
using System.Text.Json.Serialization;
using agent.session;

namespace agent.registry;


[JsonSerializable(typeof(GlobalStatusPanel))]
[JsonSerializable(typeof(AgentStatusPanel))]
[JsonSerializable(typeof(SessionListPanel))]
[JsonSerializable(typeof(SessionDetailPanel))]
[System.Text.Json.Serialization.JsonSourceGenerationOptions(WriteIndented = true)]
internal sealed partial class PanelJsonContext : JsonSerializerContext;
