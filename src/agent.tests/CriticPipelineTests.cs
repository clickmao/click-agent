using agent.critique;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.14.0 T2c CriticPipeline 单测: 双源确认/单源观察/修法库升级/渲染契约。
/// </summary>
public class CriticPipelineTests : IDisposable
{
    private readonly string _path = Path.Combine(Path.GetTempPath(), $"pipe-{Guid.NewGuid():N}.json");

    public void Dispose()
    {
        if (File.Exists(_path)) File.Delete(_path);
    }

    [Fact]
    public void StaticFindings_Confirmed_AndWritten()
    {
        var mem = FixMemory.Load(_path);
        var sf = new List<OutputCritic.Finding> { new("R01", 3, "new[] { a.In0 }", "用 ref 局部变量") };
        var (conf, obs) = CriticPipeline.Assemble(sf, Array.Empty<SelfCritic.CandidateCritique>(), mem, "任意输出");
        Assert.Single(conf);
        Assert.True(conf[0].Confirmed);
        Assert.Empty(obs);
        Assert.Single(mem.Entries); // 静态命中入修法库 (metric_delta 来源)
    }

    [Fact]
    public void LlmCandidate_CrossWithStatic_Deduped()
    {
        var mem = FixMemory.Load(_path);
        var sf = new List<OutputCritic.Finding> { new("R01", 3, "new[] { a.In0 }", "用 ref") };
        var llm = new List<SelfCritic.CandidateCritique>
        {
            new("new[] { a.In0 }", "每次迭代堆分配", "high", "ref 局部变量"),
        };
        var (conf, obs) = CriticPipeline.Assemble(sf, llm, mem, "任意");
        Assert.Single(conf);   // 静态条目一次 (LLM 交叉去重)
        Assert.Empty(obs);
        Assert.Equal(1, mem.Entries[0].Confirmations);
    }

    [Fact]
    public void LlmOnly_NoMemoryAnchor_ObservedNotConfirmed()
    {
        var mem = FixMemory.Load(_path);
        var llm = new List<SelfCritic.CandidateCritique>
        {
            new("完全新的模式片段", "某个机制解释", "low", "某个修法"),
        };
        var (conf, obs) = CriticPipeline.Assemble(Array.Empty<OutputCritic.Finding>(), llm, mem, "任意");
        Assert.Empty(conf);   // 单源不确认 (绝不进生成上下文)
        Assert.Single(obs);
        Assert.Empty(mem.Entries); // 观察态不入修法库
    }

    [Fact]
    public void LlmCandidate_MemoryHasPattern_PromotesConfirmed()
    {
        var mem = FixMemory.Load(_path);
        mem.Write("已知模式", "已有机制", "已有修法", "human_review");
        var llm = new List<SelfCritic.CandidateCritique>
        {
            new("已知模式", "LLM 独立复判机制", "high", "x"),
        };
        var (conf, obs) = CriticPipeline.Assemble(Array.Empty<OutputCritic.Finding>(), llm, mem, "任意");
        Assert.Single(conf);
        Assert.Equal("已有修法", conf[0].FixHint); // 修法库修法优先
        Assert.Equal(2, mem.Entries[0].Confirmations); // LLM 复判 = 第 2 次确认
        Assert.Empty(obs);
    }

    [Fact]
    public void Render_OnlyConfirmedShown()
    {
        var out_ = CriticPipeline.Render(new[]
        {
            new CriticPipeline.AnchoredFinding("p1", "m1", "f1", true, "static:R01"),
            new CriticPipeline.AnchoredFinding("p2", "m2", "f2", true, "llm+memory"),
        });
        Assert.Contains("p1", out_);
        Assert.Contains("p2", out_);
        Assert.Equal(string.Empty, CriticPipeline.Render(Array.Empty<CriticPipeline.AnchoredFinding>()));
    }

    [Fact]
    public void Telemetry_KvComplete()
    {
        var kv = CriticPipeline.Telemetry(staticCount: 2, llmRaw: 3, llmValid: 2, confirmed: 2, observed: 1);
        Assert.Equal(5, kv.Count());
    }
}
