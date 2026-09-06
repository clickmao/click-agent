using agent.skills;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 Skill 调度 P1 测试 (plan_skill_dispatch.md S.5 验收子集):
/// 口径命中/禁语拦截/疑似命中/冲突裁决/前置降级/注册加载。
/// </summary>
public class SkillDispatchTests
{
    private static SkillDefinition IdentitySkill() => new()
    {
        SkillId = "identity", Name = "身份说明", Domain = "identity",
        Type = SkillType.Normative, Priority = 10, Exclusive = true,
        Keywords = { "你是谁", "about yourself" },
        RegexPatterns = { "你是(谁|什么)" },
        DomainWords = { "身份" },
        ForceTemplate = "我是 AgentFramework 工业级智能体。",
        ForbiddenWords = { "人类" },
    };

    private static SkillDefinition GenericSkill() => new()
    {
        SkillId = "generic", Name = "通用", Domain = "misc",
        Type = SkillType.Normative, Priority = 1,
        Keywords = { "你是谁" },
        ForceTemplate = "通用回答: {input}",
    };

    [Fact]
    public async Task Normative_Hit_Force_Template_Used()
    {
        var dispatcher = new SkillDispatcher(new SkillRegistry());
        dispatcher.Register(IdentitySkill());
        var result = await dispatcher.DispatchAsync("你是谁?");
        Assert.NotNull(result);
        Assert.True(result!.Success);
        Assert.True(result.ForceUse);
        Assert.Equal("我是 AgentFramework 工业级智能体。", result.Content);
    }

    [Fact]
    public async Task Forbidden_Word_Blocks_Result()
    {
        var dispatcher = new SkillDispatcher(new SkillRegistry());
        var skill = IdentitySkill();
        skill.ForceTemplate = "我是由人类创造的智能体。"; // 含禁语
        dispatcher.Register(skill);
        var result = await dispatcher.DispatchAsync("你是谁?");
        Assert.NotNull(result);
        Assert.False(result!.Success);
        Assert.Equal("人类", result.ForbiddenHit);
    }

    [Fact]
    public async Task Suspected_Trigger_Domain_Word_Only()
    {
        var dispatcher = new SkillDispatcher(new SkillRegistry(), new TriggerMatcher(suspectedTrigger: true));
        dispatcher.Register(IdentitySkill());
        // v0.11.0 语义变更 (打点驱动修复): 疑似命中 (仅领域词, level=1) 不再 force 吞掉提问 —
        // 降级返回 null, 由主链走 LLM 普通推理 ("介绍快速排序" 曾被身份模板误吞)
        var result = await dispatcher.DispatchAsync("帮我看看这个身份信息怎么填");
        Assert.Null(result);
    }

    [Fact]
    public async Task No_Suspected_Trigger_Off()
    {
        var dispatcher = new SkillDispatcher(new SkillRegistry(), new TriggerMatcher(suspectedTrigger: false));
        dispatcher.Register(IdentitySkill());
        var result = await dispatcher.DispatchAsync("帮我看看这个身份信息怎么填");
        Assert.Null(result); // 疑似触发关 → 不激活
    }

    [Fact]
    public async Task Conflict_Exclusive_And_Priority_Win()
    {
        var dispatcher = new SkillDispatcher(new SkillRegistry());
        dispatcher.Register(GenericSkill());   // priority 1
        dispatcher.Register(IdentitySkill());  // priority 10 + exclusive
        var result = await dispatcher.DispatchAsync("你是谁?");
        Assert.NotNull(result);
        Assert.Equal("identity", result!.SkillId); // 排他+高优先级胜
    }

    [Fact]
    public async Task Exception_In_Entry_Degrades_To_Null()
    {
        var dispatcher = new SkillDispatcher(new SkillRegistry());
        var exec = IdentitySkill();
        exec.Type = SkillType.Executive;
        dispatcher.Register(exec);
        dispatcher.RegisterEntry("identity", (_, _) => throw new InvalidOperationException("boom"));
        var result = await dispatcher.DispatchAsync("你是谁?");
        Assert.Null(result); // 异常自动降级
    }

    [Fact]
    public async Task Executive_Entry_Executes()
    {
        var dispatcher = new SkillDispatcher(new SkillRegistry());
        var exec = IdentitySkill();
        exec.Type = SkillType.Executive;
        dispatcher.Register(exec);
        dispatcher.RegisterEntry("identity", (input, _) =>
            Task.FromResult($"执行结果: {input}"));
        var result = await dispatcher.DispatchAsync("你是谁?");
        Assert.NotNull(result);
        Assert.False(result!.ForceUse); // executive 无强制口径
        Assert.Contains("执行结果", result.Content);
    }

    [Fact]
    public void Registry_Loads_Yaml_From_Directory()
    {
        // 仓库根 skills/identity.yaml (示例技能) — 测试 cwd 是项目目录, 用相对定位
        var root = FindSkillsDir();
        if (root is null)
        {
            // 找不到目录 (CI 打包) → 跳过目录断言, 注册 API 本身已覆盖
            return;
        }
        var registry = SkillRegistry.LoadFromDirectory(root);
        // v0.10.0: 开放标准包 (SKILL.md 目录) 与 legacy 平文件并存 — legacy 断言不变
        var skill = Assert.Single(registry.All.Where(s => s.PackageDir is null));
        Assert.Equal("identity_statement", skill.SkillId);
        Assert.True(skill.Exclusive);
        Assert.Contains("你是谁", skill.Keywords);
    }

    internal static string? FindSkillsDir()
    {
        var dir = new DirectoryInfo(Directory.GetCurrentDirectory());
        for (var i = 0; i < 6 && dir is not null; i++)
        {
            var candidate = Path.Combine(dir.FullName, "skills");
            if (Directory.Exists(candidate) && Directory.EnumerateFiles(candidate, "*.y*ml").Any())
                return candidate;
            dir = dir.Parent;
        }
        return null;
    }
}
