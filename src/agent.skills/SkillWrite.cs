namespace agent.skills;


/// <summary>Skill 沙箱内写入 (暂存, 提交时校验)</summary>
public sealed class SkillWrite
{
    public string Field { get; init; } = string.Empty;
    public string Value { get; init; } = string.Empty;
}
