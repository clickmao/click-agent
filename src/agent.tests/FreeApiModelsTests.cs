using System;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using agent.modelqueue;

namespace agentframework.tests;

/// <summary>v0.20.5 R351 (用户钦定): 模型目录精简 — 仅 deepseek-4.1-flash(首)/glm-5.3-flash(次)/gpt-6(默认配置);
/// 本地 LLM/官方通道/免费池预留配置全部移除。选模: 无 key 沉底机制保留。</summary>
public class FreeApiModelsTests
{
    private static string RepoRoot()
    {
        var dir = AppContext.BaseDirectory;
        while (!string.IsNullOrEmpty(dir))
        {
            if (File.Exists(Path.Combine(dir, "config", "base", "models.yaml"))) return dir;
            dir = Path.GetDirectoryName(dir);
        }
        throw new DirectoryNotFoundException("找不到仓库根 (config/base/models.yaml)");
    }

    private static string Yaml() => File.ReadAllText(Path.Combine(RepoRoot(), "config", "base", "models.yaml"));

    [Theory]
    [InlineData("deepseek-4.1-flash", "deepseek", "https://api.deepseek.com/v1/chat/completions", "AGENTFRAMEWORK_KEYS_DEEPSEEK")]
    [InlineData("glm-5.3-flash", "zhipu", "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions", "AGENTFRAMEWORK_KEYS_BIGMODEL")]
    [InlineData("gpt-6", "openai", "https://api.openai.com/v1/chat/completions", "AGENT_OPENAI_KEY")]
    public void Yaml_ContainsExactlyThreeChannels(string name, string provider, string endpoint, string keyEnv)
    {
        var yaml = Yaml();
        Assert.Contains($"name: {name}", yaml);
        Assert.Contains($"provider: {provider}", yaml);
        Assert.Contains(endpoint, yaml);
        Assert.Contains($"api_key: {keyEnv}", yaml);
    }

    [Fact]
    public void Yaml_Stripped_OfRemovedSources()
    {
        var yaml = Yaml();
        // 本地 LLM / 官方通道 / 免费池预留 全部移除 (用户钦定)
        Assert.DoesNotContain("LocalLlamaCaller", yaml);
        Assert.DoesNotContain("\nlocal:", yaml); // 本地推理通道段已删 (bypass_local 是代理配置, 保留)
        Assert.DoesNotContain("OfficialModels", yaml);
        Assert.DoesNotContain(":free", yaml);
        Assert.DoesNotContain("groq", yaml, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("siliconflow", yaml, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("openrouter", yaml, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("kilo", yaml, StringComparison.OrdinalIgnoreCase);
        // 移除的旧预留条目
        Assert.DoesNotContain("gpt-4o", yaml);
        Assert.DoesNotContain("gemini", yaml, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("claude", yaml, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void RankCandidates_NoKey_SinksEntry()
    {
        var sched = new ChannelScheduler();
        var keyed = new ModelCatalogEntry
        {
            Id = "keyed", Provider = "remote", ReasoningScore = 5, CodingScore = 5,
            PriceInPerM = 1, PriceOutPerM = 1, ContextWindow = 128000,
            ApiKeyEnv = "AF_T_KEYED",
            SuitedFor = new List<string> { "general" },
        };
        var unkeyed = new ModelCatalogEntry
        {
            Id = "unkeyed", Provider = "remote", ReasoningScore = 9, CodingScore = 9,
            PriceInPerM = 0, PriceOutPerM = 0, ContextWindow = 128000,
            ApiKeyEnv = "AF_T_UNKEYED",
            SuitedFor = new List<string> { "general" },
        };
        var old1 = Environment.GetEnvironmentVariable("AF_T_KEYED");
        var old2 = Environment.GetEnvironmentVariable("AF_T_UNKEYED");
        try
        {
            Environment.SetEnvironmentVariable("AF_T_KEYED", "k");
            Environment.SetEnvironmentVariable("AF_T_UNKEYED", null);
            var ranked = sched.RankCandidates(new[] { unkeyed, keyed }, TaskKindHint.General, 1000);
            Assert.Equal(0, ranked.First(r => r.Model.Id == unkeyed.Id).PriceScore);
            Assert.Equal("keyed", ranked[0].Model.Id);
        }
        finally
        {
            Environment.SetEnvironmentVariable("AF_T_KEYED", old1);
            Environment.SetEnvironmentVariable("AF_T_UNKEYED", old2);
        }
    }

    [Fact]
    public void RankCandidates_FreePrice_Surfaces_WhenKeyed()
    {
        var sched = new ChannelScheduler();
        var free = new ModelCatalogEntry
        {
            Id = "glm-5.3-flash", Provider = "remote", ReasoningScore = 8, CodingScore = 8,
            PriceInPerM = 0, PriceOutPerM = 0, ContextWindow = 131072,
            ApiKeyEnv = "AF_T_FREE",
            SuitedFor = new List<string> { "general" },
        };
        var paid = new ModelCatalogEntry
        {
            Id = "paid", Provider = "remote", ReasoningScore = 8, CodingScore = 8,
            PriceInPerM = 2, PriceOutPerM = 8, ContextWindow = 128000,
            ApiKeyEnv = "AF_T_PAID",
            SuitedFor = new List<string> { "general" },
        };
        var old1 = Environment.GetEnvironmentVariable("AF_T_FREE");
        var old2 = Environment.GetEnvironmentVariable("AF_T_PAID");
        try
        {
            Environment.SetEnvironmentVariable("AF_T_FREE", "k");
            Environment.SetEnvironmentVariable("AF_T_PAID", "k");
            var ranked = sched.RankCandidates(new[] { free, paid }, TaskKindHint.General, 1000);
            Assert.Equal(1.0, ranked.First(r => r.Model.Id == free.Id).PriceScore);
            Assert.Equal(free.Id, ranked[0].Model.Id);
        }
        finally
        {
            Environment.SetEnvironmentVariable("AF_T_FREE", old1);
            Environment.SetEnvironmentVariable("AF_T_PAID", old2);
        }
    }
}
