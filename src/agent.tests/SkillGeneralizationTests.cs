using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using agent.roles;
using agent.skills;
using Xunit;

namespace agent.tests;

/// <summary>
/// R373 机检: **经验的存在形态 = 思考逻辑 skill, 且核心判据零语言特性** (用户 R373 钦定)。
///   铁律: 通用经验沉淀为 skill; 语言特有写法只在「该经验本身只关于此特性」时才可出现。
///   R1 接线级: 技能必须能被**真实加载器**载入 (不是"文件存在"就算数)
///   R2 通用化: 正文核心段落检出 语言名/扩展名/专有 API = 0
///   R3 负向控制: 注入语言 token → 检查器必红 (证明 R2 不是空转断言)
///
/// R398 扩展 (用户钦定: 经验要"总结通用性 skill 放入 skills 文件夹内"): 门禁从**单点**
///   (只认 delivery-selfcheck) 改为**全目录遍历** —— skills/ 下每个 knowledge_hint skill
///   逐个过 R1/R2/R3; 新增 skill 未过门禁 ⇒ 测试红 (防止沉淀绕过机检)。
/// </summary>
public class SkillGeneralizationTests
{
    /// <summary>必须存在且必须过门禁的基线 skill (防"目录被清空 ⇒ 遍历型断言空转全绿")。</summary>
    private static readonly string[] BaselineSkills = { "delivery-selfcheck", "independent-verification-before-claim" };

    private static readonly string RepoRoot = FindRepoRoot();

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    private static string SkillsRoot => Path.Combine(RepoRoot, "skills");

    private static string SkillMd(string skillId) => Path.Combine(SkillsRoot, skillId, "SKILL.md");

    /// <summary>去掉 front-matter 后的正文 (front-matter 的 name/description 允许英文)。</summary>
    private static string Body(string raw)
    {
        var lines = raw.Replace("\r\n", "\n").Split('\n');
        var fences = 0;
        var idx = 0;
        for (; idx < lines.Length; idx++)
        {
            if (lines[idx].Trim() == "---")
            {
                fences++;
                if (fences == 2) { idx++; break; }
            }
        }
        return string.Join("\n", lines.Skip(idx));
    }

    /// <summary>全目录遍历出的 knowledge_hint skill Id (真实加载器给的结果, 非目录名猜测)。</summary>
    private static List<string> KnowledgeHintSkillIds()
        => SkillPackageLoader.LoadPackages(SkillsRoot)
            .Where(s => s.Type == SkillType.KnowledgeHint)
            .Select(s => s.SkillId)
            .OrderBy(x => x, StringComparer.Ordinal)
            .ToList();

    [Fact]
    public void 门禁扫描面_必须覆盖基线skill且非空()
    {
        var ids = KnowledgeHintSkillIds();
        Assert.NotEmpty(ids);
        foreach (var b in BaselineSkills)
            Assert.True(ids.Contains(b), $"基线 skill 缺失或类型不是 knowledge_hint: {b} (实际: {string.Join(", ", ids)})");
    }

    [Fact]
    public void 每个思考逻辑技能_必须能被真实加载器载入()
    {
        var loaded = SkillPackageLoader.LoadPackages(SkillsRoot);
        foreach (var id in KnowledgeHintSkillIds())
        {
            var def = loaded.FirstOrDefault(s => s.SkillId == id);
            Assert.NotNull(def);
            Assert.Equal(id, def!.SkillId);
            Assert.True(File.Exists(SkillMd(id)), $"缺少思考逻辑技能文件: {SkillMd(id)}");
            Assert.False(string.IsNullOrWhiteSpace(def.Domain), $"{id}: description 必须落 Domain (语义匹配文本)");
            // 真机教训 (R373): normative 会被 force 直出 → 写代码任务被"技能正文"劫持 (无 LLM 调用, 2.4s 返回技能文档)。
            // 自检经验属"注入参考", 必须 knowledge_hint (命中注入, 回复仍走 LLM 主链)。
            Assert.Equal(SkillType.KnowledgeHint, def.Type);
            Assert.NotEmpty(def.Keywords);
            Assert.NotEmpty(def.RegexPatterns);
        }
    }

    [Fact]
    public void 每个思考逻辑技能_正文核心必须是语言无关的()
    {
        var ids = KnowledgeHintSkillIds();
        Assert.NotEmpty(ids);
        foreach (var id in ids)
        {
            var body = Body(File.ReadAllText(SkillMd(id)));
            Assert.False(string.IsNullOrWhiteSpace(body));
            var hits = LessonGeneralization.Screen(body);
            Assert.True(hits.Count == 0,
                $"{id}: 核心判据出现语言/专有 API 特性: [{string.Join(", ", hits)}] — 语言细节只能出现在『实例』章节");
        }
    }

    [Fact]
    public void 负向控制_注入语言token必被检出()
    {
        foreach (var id in KnowledgeHintSkillIds())
        {
            var poisoned = Body(File.ReadAllText(SkillMd(id)))
                + "\n- 实现要点: 用 Python 的 asyncio 重写事件循环。\n";
            var hits = LessonGeneralization.Screen(poisoned);
            Assert.Contains("python", hits);
        }
    }
}
