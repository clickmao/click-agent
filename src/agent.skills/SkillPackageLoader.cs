using agent.config;

namespace agent.skills;

/// <summary>
/// v0.10.0 新需求5: Anthropic Agent-Skills Open Standard (SKILL.md 文件夹包格式) 加载器。
/// 开放规范 (agentskills.io — OpenAI 等多家 Agent 框架兼容此打包规范):
/// <code>
/// skill-name/                # 目录名必须等于 front-matter name; kebab-case 小写
/// ├── SKILL.md               # 【强制】YAML front-matter + Markdown 正文
/// ├── scripts/               # 可选: py/sh 可执行脚本
/// ├── references/            # 可选: 大段参考文档、openapi、样例 (不塞 SKILL.md)
/// └── assets/                # 可选: 模板、静态资源
/// </code>
/// front-matter 字段映射 (开放规范 → 内部 SkillDefinition):
///   name → SkillId + Name; description → Domain (语义匹配文本) + 触发依据;
///   兼容扩展: keywords / regex_patterns / domain_words / priority / exclusive /
///           force_template / forbidden_words / type / version / timeout_seconds
/// (开放规范核心字段 name+description 必填, 其余为本框架触发调度扩展 — 双向兼容:
///  外部生态包缺扩展字段 → 纯语义/关键词调度; 本框架包可带完整触发词)
/// </summary>
public static class SkillPackageLoader
{
    /// <summary>
    /// 扫描 skillRoot 下全部子目录: 含 SKILL.md 的目录按开放规范包加载。
    /// 兼容并存: 同目录下 legacy *.yaml 平文件由 SkillRegistry.LoadFromDirectory 处理。
    /// </summary>
    /// <summary>加载单个 SKILL.md 包 (测试/动态注册; 目录名=front-matter name 铁律同 LoadPackages)。</summary>
    public static SkillDefinition? LoadPackage(string packageDir)
    {
        var skillMd = Path.Combine(packageDir, "SKILL.md");
        return File.Exists(skillMd) ? ParseSkillMd(File.ReadAllText(skillMd), packageDir) : null;
    }

    public static List<SkillDefinition> LoadPackages(string skillRoot)
    {
        var results = new List<SkillDefinition>();
        if (!Directory.Exists(skillRoot))
            return results;
        foreach (var dir in Directory.EnumerateDirectories(skillRoot))
        {
            var skillMd = Path.Combine(dir, "SKILL.md");
            if (!File.Exists(skillMd))
                continue;
            try
            {
                var skill = ParseSkillMd(File.ReadAllText(skillMd), dir);
                if (skill is not null)
                    results.Add(skill);
                else
                    agent.config.AgentTelemetry.Emit("skill_parse", "SkillPackageLoader",
                        ("dir", Path.GetFileName(dir)), ("result", "null"));
            }
            catch (Exception ex)
            {
                agent.config.AgentTelemetry.Emit("skill_parse", "SkillPackageLoader",
                    ("dir", Path.GetFileName(dir)), ("error", ex.Message));
            }
        }
        return results;
    }

    /// <summary>解析 SKILL.md (front-matter YAML + Markdown 正文) → SkillDefinition</summary>
    internal static SkillDefinition? ParseSkillMd(string content, string packageDir)
    {
        var (frontMatter, body) = SplitFrontMatter(content);

        // 开放规范: front-matter 必含 name (目录名必须等于 name — 校验)
        var doc = MiniYaml.Parse(frontMatter);
        if (!doc.TryGetValue("name", out var nameObj) || nameObj is not string name || name.Length == 0)
            return null;
        var dirName = Path.GetFileName(Path.TrimEndingDirectorySeparator(packageDir));
        if (!string.Equals(dirName, name, StringComparison.OrdinalIgnoreCase))
            return null; // 规范铁律: 目录名 = front-matter name

        var s = new SkillDefinition
        {
            SkillId = name,
            Name = name,
            Domain = Str(doc, "description"),
            Version = StrOr(doc, "version", "1.0"),
        };

        // type: 开放规范无此字段; license/metadata 忽略 — 本框架扩展字段全兼容
        if (Str(doc, "type").Equals("executive", StringComparison.OrdinalIgnoreCase))
            s.Type = SkillType.Executive;
        if (doc.TryGetValue("priority", out var p)) s.Priority = Convert.ToInt32(p);
        if (doc.TryGetValue("exclusive", out var ex)) s.Exclusive = Convert.ToBoolean(ex);
        if (doc.TryGetValue("timeout_seconds", out var to)) s.TimeoutSeconds = Convert.ToInt32(to);
        if (doc.TryGetValue("force_template", out var ft) && ft is string ftv) s.ForceTemplate = ftv;

        s.Keywords = ReadList(doc, "keywords");
        s.RegexPatterns = ReadList(doc, "regex_patterns");
        s.DomainWords = ReadList(doc, "domain_words");
        s.ForbiddenWords = ReadList(doc, "forbidden_words");

        // Markdown 正文 = 口径正文 (normative force 承载): front-matter 无 force_template 时
        // 用正文 Markdown 作为模板基底 (开放规范: SKILL.md 正文即技能工作流/规则文档)
        if (s.ForceTemplate is null && body.Trim().Length > 0)
            s.ForceTemplate = body.Trim();

        // 语义匹配代表文本增强: description 缺失时用正文前 200 字符 (bge 嵌入目标)
        if (s.Domain.Length == 0 && body.Trim().Length > 0)
            s.Domain = body.Trim()[..Math.Min(200, body.Trim().Length)];

        // 目录结构登记 (scripts/references/assets 存在性 — 审计与后续执行调度用)
        s.PackageDir = packageDir;
        s.HasScripts = Directory.Exists(Path.Combine(packageDir, "scripts"));
        s.HasReferences = Directory.Exists(Path.Combine(packageDir, "references"));
        s.HasAssets = Directory.Exists(Path.Combine(packageDir, "assets"));
        return s;
    }

    /// <summary>分隔 YAML front-matter (--- 定界) 与 Markdown 正文</summary>
    private static (string FrontMatter, string Body) SplitFrontMatter(string content)
    {
        content = content.Replace("\r\n", "\n");
        if (!content.StartsWith("---\n", StringComparison.Ordinal))
            return (string.Empty, content);
        var end = content.IndexOf("\n---\n", 4, StringComparison.Ordinal);
        if (end < 0)
            return (string.Empty, content);
        var front = content[4..end];
        var body = content[(end + 5)..];
        return (front, body);
    }

    private static string Str(Dictionary<string, object?> doc, string key)
        => doc.TryGetValue(key, out var v) && v is string sv ? sv : string.Empty;

    private static string StrOr(Dictionary<string, object?> doc, string key, string fallback)
        => doc.TryGetValue(key, out var v) && v is string sv && sv.Length > 0 ? sv : fallback;

    private static List<string> ReadList(Dictionary<string, object?> doc, string key)
    {
        if (doc.TryGetValue(key, out var raw) && raw is List<object?> list)
            return list.Where(x => x is string).Select(x => (string)x!).ToList();
        return new List<string>();
    }
}
