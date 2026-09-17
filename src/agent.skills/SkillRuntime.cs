using agent.config;

namespace agent.skills;


/// <summary>会话内单个 Skill 的运行时状态</summary>
public sealed class SkillRuntime
{
    public SkillDefinition Skill { get; init; } = null!;
    public SkillState State { get; set; } = SkillState.Unloaded;
    public DateTimeOffset ActivatedAt { get; set; }
    public DateTimeOffset LastUsedAt { get; set; }
    public int OffTopicRounds { get; set; }

    /// <summary>熔断: 连续失败计数 / 熔断开启截止时刻</summary>
    public int ConsecutiveFailures { get; set; }
    public DateTimeOffset BreakerOpenUntil { get; set; }
}
