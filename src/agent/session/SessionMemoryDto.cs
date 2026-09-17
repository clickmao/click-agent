using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.session;


/// <summary>落盘 DTO (与领域类型解耦, source-gen 友好)</summary>
public sealed class SessionMemoryDto
{
    public string SessionId { get; set; } = string.Empty;
    public int MaxChars { get; set; }
    public string LongTermMemory { get; set; } = string.Empty;
    public int EntryCount { get; set; }
    public string? GoalText { get; set; }
    public List<string>? KeyEntities { get; set; }
    public List<string>? Constraints { get; set; }
    public List<string>? Milestones { get; set; }

    public static SessionMemoryDto From(string sessionId, SessionMemory m)
    {
        var goal = m.Goal;
        return new SessionMemoryDto
        {
            SessionId = sessionId,
            MaxChars = m.MaxChars,
            LongTermMemory = m.LongTermMemory,
            EntryCount = m.EntryCount,
            GoalText = goal?.GoalText,
            KeyEntities = goal?.KeyEntities,
            Constraints = goal?.Constraints,
            Milestones = goal?.Milestones,
        };
    }

    public GoalProfile? ToGoal()
    {
        if (string.IsNullOrEmpty(GoalText))
            return null;
        return new GoalProfile
        {
            GoalText = GoalText,
            KeyEntities = KeyEntities ?? new List<string>(),
            Constraints = Constraints ?? new List<string>(),
            Milestones = Milestones ?? new List<string>(),
        };
    }
}
