using System;
using Xunit;
using agent.llamacpp;

namespace agentframework.tests;

/// <summary>
/// R410: 生成口径 → 请求参数的映射负控（纯逻辑，不需要 llama-server）。
/// 判据预注册:
///   - Session 口径必须开 cache_prompt（K2b 前缀复用的唯一来源）；
///   - Reconciliation 口径必须关 cache_prompt（否则对账不可复现）；
///   - greedy 只留 temperature 采样器（与 R407 对账口径同构）。
/// </summary>
public sealed class CompletionReuseTests
{
    [Fact]
    public void Session_EnablesCachePrompt()
    {
        var o = CompletionProfiles.Build("p", 8, greedy: true, CompletionReuse.Session);
        Assert.True(o.CachePrompt);
    }

    [Fact]
    public void Reconciliation_DisablesCachePrompt()
    {
        var o = CompletionProfiles.Build("p", 8, greedy: true, CompletionReuse.Reconciliation);
        Assert.False(o.CachePrompt);
    }

    [Fact]
    public void Greedy_UsesOnlyTemperatureSampler()
    {
        var o = CompletionProfiles.Build("p", 8, greedy: true, CompletionReuse.Session);
        Assert.Equal(new[] { "temperature" }, o.Samplers);
        Assert.Equal(0f, o.Temperature);
        Assert.Equal("p", o.Prompt);
        Assert.Equal(8, o.MaxTokens);
    }

    [Fact]
    public void NonGreedy_KeepsFullSamplerChain()
    {
        var o = CompletionProfiles.Build("p", 8, greedy: false, CompletionReuse.Session);
        Assert.Equal(new[] { "top_k", "top_p", "min_p", "temperature" }, o.Samplers);
        Assert.True(o.Temperature > 0f);
    }
}
