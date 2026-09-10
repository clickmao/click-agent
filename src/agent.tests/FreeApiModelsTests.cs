using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Xunit;
using agent.modelqueue;

namespace agentframework.tests;

/// <summary>v0.20.4 (R347): 免费国外 API 备用池 — YAML 条目 + auto 沉底机制
/// (未配 key → priceScore=0 沉底, 对现有选择零影响; 配 key → 价格 0 → 自动进入优选/兜底)。</summary>
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

    [Theory]
    [InlineData("llama-3.3-70b-versatile", "groq", "https://api.groq.com/openai/v1/chat/completions", "AGENT_GROQ_KEY")]
    [InlineData("llama-3.1-8b-instant", "groq", "https://api.groq.com/openai/v1/chat/completions", "AGENT_GROQ_KEY")]
    [InlineData("openai/gpt-oss-120b", "groq", "https://api.groq.com/openai/v1/chat/completions", "AGENT_GROQ_KEY")]
    [InlineData("nvidia/nemotron-3-ultra-550b-a55b:free", "openrouter", "https://openrouter.ai/api/v1/chat/completions", "AGENT_OPENROUTER_KEY")]
    [InlineData("nvidia/nemotron-3-super-120b-a12b:free", "openrouter", "https://openrouter.ai/api/v1/chat/completions", "AGENT_OPENROUTER_KEY")]
    [InlineData("siliconflow-glm-4-9b", "siliconflow", "https://api.siliconflow.cn/v1/chat/completions", "AGENT_SILICONFLOW_KEY")]
    [InlineData("deepseek-ai/DeepSeek-V4-Flash", "modelscope", "https://api-inference.modelscope.cn/v1/chat/completions", "AGENT_MODELSCOPE_KEY")]
    [InlineData("moonshotai/kimi-k2.6", "nvidia", "https://integrate.api.nvidia.com/v1/chat/completions", "AGENT_NVIDIA_KEY")]
    [InlineData("cohere-command-a-reasoning", "cohere", "https://api.cohere.ai/compatibility/v1/chat/completions", "AGENT_COHERE_KEY")]
    [InlineData("kilo-free", "kilo", "https://api.kilo.ai/api/gateway/chat/completions", "AGENT_KILO_KEY")]
    [InlineData("openrouter/free", "openrouter", "https://openrouter.ai/api/v1/chat/completions", "AGENT_OPENROUTER_KEY")]
    [InlineData("gemini-3.5-flash", "google", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "AGENT_GEMINI_KEY")]
    [InlineData("llama-3.3-70b", "cerebras", "https://api.cerebras.ai/v1/chat/completions", "AGENT_CEREBRAS_KEY")]
    [InlineData("nvidia/llama-3.1-nemotron-70b-instruct", "nvidia", "https://integrate.api.nvidia.com/v1/chat/completions", "AGENT_NVIDIA_KEY")]
    public void Yaml_ContainsFreeApiEntry(string name, string provider, string endpoint, string keyEnv)
    {
        // YAML 原文校验 (不依赖 ConfigSnapshot 语义; 防条目漂移)
        var yaml = File.ReadAllText(Path.Combine(RepoRoot(), "config", "base", "models.yaml"));
        Assert.True(yaml.Contains($"name: {name}") || yaml.Contains($"name: \"{name}\"") || yaml.Contains($"name: '{name}'"),
            $"YAML 未含条目 name={name} (含引号形式)");
        Assert.Contains($"provider: {provider}", yaml);
        Assert.Contains(endpoint, yaml);
        Assert.Contains($"api_key: {keyEnv}", yaml);
    }

    [Fact]
    public void FreeEntries_HaveZeroPrice()
    {
        var yaml = File.ReadAllText(Path.Combine(RepoRoot(), "config", "base", "models.yaml"));
        var lines = yaml.Split('\n');
        // 免费段内所有条目 price 均为 0.0 (免费语义: 不打价格战误判)
        var start = Array.FindIndex(lines, l => l.Contains("免费国外 API 备用池"));
        Assert.True(start > 0, "未找到免费备用池段");
        var seg = string.Join('\n', lines[start..]);
        var inFree = seg.Split("proxy:")[0];
        var nameCount = inFree.Split("  - name:").Length - 1;
        var zeroPrice = inFree.Split("price_in_per_m: 0.0").Length - 1;
        Assert.True(nameCount is >= 27 and <= 29, $"免费条目数应为 27-29 (8 原有+19 新增-去重), 实际 {nameCount}");
        Assert.Equal(nameCount, zeroPrice);
    }

    [Fact]
    public void RankCandidates_NoKey_SinksFreeEntries()
    {
        // 免费模型价格 0 → priceScore 计算为 1; 但 env 未配置 → 强降权 0 → 沉底
        var sched = new ChannelScheduler();
        var free = MakeEntry("llama-3.3-70b-versatile", "groq", "AGENT_GROQ_KEY", 0, 0, 7);
        var paid = MakeEntry("glm-5.3-flash", "zhipu", "AGENT_ZHIPU_KEY", 1, 1, 7);
        var oldGroq = Environment.GetEnvironmentVariable("AGENT_GROQ_KEY");
        var oldZhipu = Environment.GetEnvironmentVariable("AGENT_ZHIPU_KEY");
        try
        {
            Environment.SetEnvironmentVariable("AGENT_GROQ_KEY", null);
            Environment.SetEnvironmentVariable("AGENT_ZHIPU_KEY", "test-key");
            var ranked = sched.RankCandidates(new[] { free, paid }, TaskKindHint.General, 1000);
            Assert.Equal(0, ranked.First(r => r.Model.Id == free.Id).PriceScore);
            Assert.Equal(paid.Id, ranked[0].Model.Id); // 无 key 免费条目沉底 (不影响现有选择)
        }
        finally
        {
            Environment.SetEnvironmentVariable("AGENT_GROQ_KEY", oldGroq);
            Environment.SetEnvironmentVariable("AGENT_ZHIPU_KEY", oldZhipu);
        }
    }

    [Fact]
    public void RankCandidates_WithKey_FreeEntrySurfaces()
    {
        // 配 key 后: 免费 (价格 0 → priceScore=1) 与付费模型同等能力下 → 免费排前 (auto 优选)
        var sched = new ChannelScheduler();
        var free = MakeEntry("llama-3.3-70b-versatile", "groq", "AGENT_GROQ_KEY", 0, 0, 7);
        var paid = MakeEntry("glm-5.3-flash", "zhipu", "AGENT_ZHIPU_KEY", 2, 8, 7);
        var oldGroq = Environment.GetEnvironmentVariable("AGENT_GROQ_KEY");
        var oldZhipu = Environment.GetEnvironmentVariable("AGENT_ZHIPU_KEY");
        try
        {
            Environment.SetEnvironmentVariable("AGENT_GROQ_KEY", "test-key");
            Environment.SetEnvironmentVariable("AGENT_ZHIPU_KEY", "test-key");
            var ranked = sched.RankCandidates(new[] { free, paid }, TaskKindHint.General, 1000);
            Assert.Equal(1.0, ranked.First(r => r.Model.Id == free.Id).PriceScore);
            Assert.Equal(free.Id, ranked[0].Model.Id);
        }
        finally
        {
            Environment.SetEnvironmentVariable("AGENT_GROQ_KEY", oldGroq);
            Environment.SetEnvironmentVariable("AGENT_ZHIPU_KEY", oldZhipu);
        }
    }

    private static ModelCatalogEntry MakeEntry(string id, string provider, string keyEnv,
        int priceIn, int priceOut, int reasoning)
        => new()
        {
            Id = id,
            Provider = provider,
            ApiKeyEnv = keyEnv,
            PriceInPerM = priceIn,
            PriceOutPerM = priceOut,
            ReasoningScore = reasoning,
            CodingScore = reasoning,
            ContextWindow = 131072,
            SuitedFor = new List<string> { "general", "chat" },
        };
}
