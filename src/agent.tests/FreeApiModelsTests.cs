using System;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using agent.modelqueue;

namespace agentframework.tests;

/// <summary>v0.20.5 R351 (用户钦定): 模型目录精简 — 仅 deepseek-flash(首)/glm-5.3-flash(次)/gpt-6(默认配置);
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
    [InlineData("deepseek-flash", "deepseek", "https://api.deepseek.com/v1/chat/completions", "AGENTFRAMEWORK_KEYS_DEEPSEEK")]
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
    public void Yaml_LocalBlock_DiscriminatorOnly()
    {
        // R463 (用户令「改用3b」): `local:` 段仅作判别通道存在, 边界机检。
        // 存在性 = 允许 (计划节点); 但一旦存在, 下列不变量必须成立:
        //   ① 不得开启通用本地推理 (allow_general: false);
        //   ② 必须显式声明 turn_gate / relation_judge 与 model_path (禁隐式默认);
        //   ③ allowed_kinds 不得含通用对话 kind; model_path 必须是绝对 .gguf;
        //   ④ 权重文件若在盘上, 体量必须 > 100 MB (防 0 字节/占位文件被当权重)。
        var yaml = Yaml();
        var idx = yaml.IndexOf("\nlocal:", StringComparison.Ordinal);
        if (idx < 0) return; // 未配置判别通道 ⇒ 合法
        var block = yaml.Substring(idx + 1);
        var end = block.IndexOf("\n\n", StringComparison.Ordinal);
        if (end >= 0) block = block.Substring(0, end);

        Assert.Contains("allow_general: false", block);
        Assert.Contains("turn_gate:", block);
        Assert.Contains("relation_judge:", block);
        Assert.DoesNotContain("chat", block, StringComparison.OrdinalIgnoreCase);

        var pathLine = block.Split('\n').First(l => l.TrimStart().StartsWith("model_path:", StringComparison.Ordinal));
        var path = pathLine.Substring(pathLine.IndexOf(':') + 1).Trim();
        Assert.StartsWith("/", path);
        Assert.EndsWith(".gguf", path);
        var fi = new FileInfo(path);
        if (fi.Exists) Assert.True(fi.Length > 100 * 1024 * 1024, $"权重体量异常: {fi.Length} B");
    }

    [Fact]
    public void Yaml_Stripped_OfRemovedSources()
    {
        var yaml = Yaml();
        // 本地 LLM / 官方通道 / 免费池预留 全部移除 (用户钦定)
        Assert.DoesNotContain("LocalLlamaCaller", yaml);
        // R463 修订 (用户令「改用3b」+ R351 口径澄清「移除的是本地 llm **使用**, 新增的 r1 判别是计划节点」):
        //   `local:` 段不再一律禁止 —— 只允许作**判别通道** (turn_gate / relation_judge),
        //   禁止回到「通用本地 LLM 对话/推理」。边界由 Yaml_LocalBlock_DiscriminatorOnly 机检。
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
