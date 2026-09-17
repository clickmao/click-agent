using agent.config;

namespace agent.skills;


/// <summary>Skill 生命周期状态 (原文 §3.4: Unloaded→Loaded→Active→Suspended→Unloaded)</summary>
public enum SkillState
{
    Unloaded,
    Loaded,
    Active,
    Suspended,
}
