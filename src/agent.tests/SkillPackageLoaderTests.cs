using System.IO;
using agent.skills;
using Xunit;

namespace agent.tests;

/// <summary>
/// v0.10.0 新需求5: Anthropic Agent-Skills Open Standard (SKILL.md 包格式) 加载器契约。
///   ① 开放标准包 (目录/SKILL.md/front-matter) 正确解析: name 必填, 目录名=name
///   ② 扩展字段 (keywords/regex/priority) 双向兼容: 缺省走语义/正文调度
///   ③ 目录名 ≠ front-matter name → 拒绝 (规范铁律)
///   ④ legacy 平文件与开放包并存加载
/// </summary>
public class SkillPackageLoaderTests
{
    private static string WritePackage(string root, string dirName, string frontMatter, string body)
    {
        var dir = Path.Combine(root, dirName);
        Directory.CreateDirectory(dir);
        File.WriteAllText(Path.Combine(dir, "SKILL.md"), $"---\n{frontMatter}\n---\n\n{body}");
        return dir;
    }

    [Fact]
    public void OpenStandard_Package_Parses_Core_Fields()
    {
        var root = Path.Combine(Path.GetTempPath(), "skillpkg", Guid.NewGuid().ToString("N"));
        try
        {
            WritePackage(root, "demo-skill",
                "name: demo-skill\ndescription: 演示技能说明",
                "# Demo\n\n正文工作流文档。");
            var skills = SkillPackageLoader.LoadPackages(root);
            Assert.Single(skills);
            var s = skills[0];
            Assert.Equal("demo-skill", s.SkillId);
            Assert.Equal("演示技能说明", s.Domain);
            Assert.NotNull(s.ForceTemplate);          // normative: 正文 = force 模板基底
            Assert.Contains("# Demo", s.ForceTemplate);
            Assert.NotNull(s.PackageDir);
        }
        finally { Directory.Delete(root, true); }
    }

    [Fact]
    public void Extension_Fields_Map_To_Scheduling()
    {
        var root = Path.Combine(Path.GetTempPath(), "skillpkg", Guid.NewGuid().ToString("N"));
        try
        {
            WritePackage(root, "commit-helper",
                string.Join("\n",
                    "name: commit-helper",
                    "description: 提交信息辅助",
                    "priority: 8",
                    "exclusive: true",
                    "keywords:",
                    "  - 提交信息",
                    "regex_patterns:",
                    "  - \"(写|生成)commit\""),
                "# Helper");
            var skills = SkillPackageLoader.LoadPackages(root);
            Assert.Single(skills);
            var s = skills[0];
            Assert.Equal(8, s.Priority);
            Assert.True(s.Exclusive);
            Assert.Contains("提交信息", s.Keywords);
            Assert.Single(s.RegexPatterns);
        }
        finally { Directory.Delete(root, true); }
    }

    [Fact]
    public void DirName_Must_Equal_FrontMatter_Name()
    {
        var root = Path.Combine(Path.GetTempPath(), "skillpkg", Guid.NewGuid().ToString("N"));
        try
        {
            WritePackage(root, "wrong-name", "name: other-name\ndescription: x", "# X");
            Assert.Empty(SkillPackageLoader.LoadPackages(root)); // 铁律: 目录名=name
        }
        finally { Directory.Delete(root, true); }
    }

    [Fact]
    public void Registry_Loads_OpenStandard_Packages()
    {
        // 仓库根 skills/: 开放包 (git-commit-helper, code-review-checklist) + legacy (identity.yaml) 并存
        var repoRoot = AppContext.BaseDirectory;
        for (var i = 0; i < 6; i++)
        {
            if (Directory.Exists(Path.Combine(repoRoot, "skills")))
                break;
            repoRoot = Path.GetFullPath(Path.Combine(repoRoot, ".."));
        }
        var skillsDir = Path.Combine(repoRoot, "skills");
        if (!Directory.Exists(skillsDir))
            return; // 定位失败跳过 (不误报)

        var registry = SkillRegistry.LoadFromDirectory(skillsDir);
        // 开放包已注册
        Assert.Contains(registry.All, s => s.SkillId == "git-commit-helper");
        Assert.Contains(registry.All, s => s.SkillId == "code-review-checklist");
        // legacy 平文件仍注册 (兼容并存)
        Assert.Contains(registry.All, s => s.SkillId == "identity_statement");
        // 开放包带扩展调度字段
        var commit = registry.All.First(s => s.SkillId == "git-commit-helper");
        Assert.NotEmpty(commit.Keywords);
        Assert.NotEmpty(commit.RegexPatterns);
    }
}
