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

/// <summary>
/// 三级触发匹配 (原文 §5): 一级关键词 → 二级正则精匹配 → 领域词疑似。
/// 裁决: 排他 > 优先级 > 精确度 (S.5 冲突四组合覆盖)。
/// </summary>
public sealed class TriggerMatcher
{
    private readonly bool _suspectedTrigger;

    public TriggerMatcher(bool suspectedTrigger = true) => _suspectedTrigger = suspectedTrigger;

    /// <summary>返回全部命中 (已按裁决排序; 空 = 未命中)</summary>
    public List<SkillMatch> Match(string input, List<SkillDefinition> skills)
    {
        var hits = new List<SkillMatch>();
        foreach (var s in skills)
        {
            var level = 0;
            double precision = 0;

            // 一级: 关键词 (包含匹配)
            var keywordHit = s.Keywords.Any(k =>
                k.Length > 0 && input.Contains(k, StringComparison.OrdinalIgnoreCase));
            if (keywordHit)
            {
                level = 2;
                precision = 0.6;
            }

            // 二级: 正则精匹配 (覆盖一级 — 更精确)
            foreach (var pattern in s.RegexPatterns)
            {
                try
                {
                    if (Regex.IsMatch(input, pattern, RegexOptions.IgnoreCase))
                    {
                        level = 3;
                        precision = 0.95;
                        break;
                    }
                }
                catch (ArgumentException)
                {
                    // 坏正则跳过 (定义文件错误不崩调度)
                }
            }

            // 疑似: 无关键词/正则命中但有领域词
            if (level == 0 && _suspectedTrigger && s.DomainWords.Any(w =>
                    w.Length > 0 && input.Contains(w, StringComparison.OrdinalIgnoreCase)))
            {
                level = 1;
                precision = 0.3;
            }

            if (level > 0)
                hits.Add(new SkillMatch { Skill = s, Level = level, Precision = precision });
        }

        // 裁决: 排他 > 优先级 > 精确度 > 匹配级别
        return hits
            .OrderByDescending(m => m.Skill.Exclusive)
            .ThenByDescending(m => m.Skill.Priority)
            .ThenByDescending(m => m.Precision)
            .ThenByDescending(m => m.Level)
            .ToList();
    }
}
