using System.Text.RegularExpressions;

namespace agent.skills;


/// <summary>匹配结果 (裁决排序用)</summary>
public sealed class SkillMatch
{
    public SkillDefinition Skill { get; set; } = null!;

    /// <summary>0=未命中 1=疑似(仅领域词) 2=关键词 3=正则精匹配</summary>
    public int Level { get; set; }

    /// <summary>精确度 (正则>关键词>领域词)</summary>
    public double Precision { get; set; }
}
