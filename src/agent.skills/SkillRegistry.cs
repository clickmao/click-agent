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
        // v0.10.0 新需求5: 开放规范包优先 (skill-name/SKILL.md 目录包格式)
        foreach (var pkg in SkillPackageLoader.LoadPackages(skillRoot))
            registry.Register(pkg);
        agent.config.AgentTelemetry.Emit("skill_load", "SkillRegistry",
            ("root", System.IO.Path.GetFullPath(skillRoot)), ("cwd", System.Environment.CurrentDirectory), ("count", registry.All.Count), ("ids", string.Join(",", registry.All.Select(x => x.SkillId))));
        // legacy 平文件 (*.yaml) 兼容并存 (identity.yaml 等存量技能)
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

    /// <summary>v0.16.0-a: blacklist 移除 — 精确 SkillId 匹配, 或目录名前缀 (skill 包目录名) 匹配。</summary>
    public int RemoveById(string idOrDir)
    {
        lock (_lock)
        {
            var exact = _skills.Keys.Where(k => k == idOrDir).ToList();
            var byDir = _skills.Where(kv => Path.GetFileName(kv.Value.PackageDir ?? "") == idOrDir)
                               .Select(kv => kv.Key).ToList();
            var removed = 0;
            foreach (var k in exact.Concat(byDir).Distinct())
            {
                if (_skills.Remove(k)) removed++;
            }
            return removed;
        }
    }

    // v0.16.0-b: 运行时动态过滤 (循环任务内 whitelist/blacklist — AgentFramework_Skills_ActiveWhitelist/Blacklist env 或指令设置)
    private volatile HashSet<string>? _activeWhitelist; // null = 不过滤
    private volatile HashSet<string>? _activeBlacklist; // null = 不过滤

    /// <summary>动态 whitelist (只允许这些 SkillId; null=清除)。</summary>
    public void SetActiveWhitelist(IEnumerable<string>? ids)
        => _activeWhitelist = ids is null ? null : new HashSet<string>(ids);
    /// <summary>动态 blacklist (排除这些 SkillId; null=清除)。</summary>
    public void SetActiveBlacklist(IEnumerable<string>? ids)
        => _activeBlacklist = ids is null ? null : new HashSet<string>(ids);

    public List<SkillDefinition> All
    {
        get
        {
            lock (_lock)
            {
                var vals = _skills.Values.ToList();
                var wl = _activeWhitelist;
                var bl = _activeBlacklist;
                if (wl is not null) vals = vals.Where(s => wl.Contains(s.SkillId)).ToList();
                if (bl is not null) vals = vals.Where(s => !bl.Contains(s.SkillId)).ToList();
                return vals;
            }
        }
    }
}
