using System.Text.Json;
using System.Text.Json.Serialization;
using agent.session;

namespace agent.registry;


public sealed class GoalEntry
{
    public string GoalText { get; set; } = string.Empty;
    public List<string> KeyEntities { get; set; } = new();
    public List<string> Constraints { get; set; } = new();
    public List<string> Milestones { get; set; } = new();
}
