using agent.config;

namespace agent.skills;

/// <summary>
/// Skill 注册中心 (原文 §3): skills/ 目录静态扫描加载 + 动态注册 API。
/// 定义文件 = MiniYaml 解析 (skill.yaml 格式见 plan_skill_dispatch S.2/原文 §7.1)。
/// </summary>
public sealed class SkillRegistry
{
    private readonly object _lock = new();
    private readonly Dictionary<string, SkillDefinition> _skills = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>目录静态加载 (skillRoot 下 *.yaml / *.yml, 每文件一个 Skill)</summary>
    public static SkillRegistry LoadFromDirectory(string skillRoot)
    {
        var registry = new SkillRegistry();
        if (!Directory.Exists(skillRoot))
            return registry;
        foreach (var file in Directory.EnumerateFiles(skillRoot, "*.y*ml"))
        {
            try
            {
                var doc = MiniYaml.Parse(File.ReadAllText(file));
                var skill = Parse(doc);
                if (skill is not null && skill.SkillId.Length > 0)
                    registry.Register(skill);
            }
            catch
            {
                // 单文件坏不阻断其他 Skill 加载 (S.5 降级原则 — 加载失败只损失该技能)
            }
        }
        return registry;
    }

    internal static SkillDefinition? Parse(Dictionary<string, object?> doc)
    {
        var s = new SkillDefinition();
        if (doc.TryGetValue("skill_id", out var id) && id is string v) s.SkillId = v;
        if (doc.TryGetValue("name", out var n) && n is string nv) s.Name = nv;
        if (doc.TryGetValue("version", out var ver) && ver is string vv) s.Version = vv;
        if (doc.TryGetValue("domain", out var d) && d is string dv) s.Domain = dv;
        if (doc.TryGetValue("type", out var t) && t is string tv &&
            tv.Equals("executive", StringComparison.OrdinalIgnoreCase))
            s.Type = SkillType.Executive;
        if (doc.TryGetValue("priority", out var p)) s.Priority = Convert.ToInt32(p);
        if (doc.TryGetValue("exclusive", out var ex)) s.Exclusive = Convert.ToBoolean(ex);
        if (doc.TryGetValue("timeout_seconds", out var to)) s.TimeoutSeconds = Convert.ToInt32(to);
        if (doc.TryGetValue("force_template", out var ft) && ft is string ftv) s.ForceTemplate = ftv;
        s.Keywords = ReadList(doc, "keywords");
        s.RegexPatterns = ReadList(doc, "regex_patterns");
        s.DomainWords = ReadList(doc, "domain_words");
        s.ForbiddenWords = ReadList(doc, "forbidden_words");
        return s;
    }

    private static List<string> ReadList(Dictionary<string, object?> doc, string key)
    {
        if (doc.TryGetValue(key, out var raw) && raw is List<object?> list)
            return list.Where(x => x is string).Select(x => (string)x!).ToList();
        return new List<string>();
    }

    public void Register(SkillDefinition skill)
    {
        lock (_lock)
        {
            _skills[skill.SkillId] = skill;
        }
    }

    public List<SkillDefinition> All
    {
        get
        {
            lock (_lock)
            {
                return _skills.Values.ToList();
            }
        }
    }
}
