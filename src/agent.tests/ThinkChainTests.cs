using agent.exploration;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.13.0 T3 M-A/M-B — 复杂度门 + 依据置信 + 思考记忆 (RAG 联想) 单测。
/// 覆盖用户钦定语义: 多源对比 (单源封顶)、RAG 偏好优先阅览、引用后稍微提升置信、负样本降权、衰减。
/// </summary>
public class ThinkChainTests
{
    // ── ComplexityGate ──
    [Fact]
    public void Simple_Question_Not_Complex()
    {
        var v = ComplexityGate.Evaluate("1+1等于几", "general", 1);
        Assert.False(v.IsComplex);
        Assert.Empty(v.Triggers);
    }

    [Fact]
    public void Complex_Multi_Trigger()
    {
        var v = ComplexityGate.Evaluate("对比 https://a.com 和 https://b.com 哪个更好, 详细区别", "research", 2);
        Assert.True(v.IsComplex);
        Assert.Contains("has_url", v.Triggers);
        Assert.Contains("subtasks>=2", v.Triggers);
    }

    [Fact]
    public void Url_Alone_Triggers_Exploration()
    {
        var v = ComplexityGate.Evaluate("总结 https://example.com/spec 的内容要点", "general", 1);
        Assert.True(v.IsComplex); // has_url(2) + path_like(2) = 4 ≥ 3
    }

    // ── EvidenceScorer ──
    private static EvidenceItem Ev(string domain, double hist, double rel) =>
        new() { Domain = domain, SourceHistoryConfidence = hist, Relevance = rel };

    [Fact]
    public void Two_Independent_Sources_Beat_Single()
    {
        var one = new List<EvidenceItem> { Ev("a.com", 0.9, 0.9) };
        var two = new List<EvidenceItem> { Ev("a.com", 0.9, 0.9), Ev("b.org", 0.9, 0.9) };
        Assert.True(EvidenceScorer.Score(two) > EvidenceScorer.Score(one));
    }

    [Fact]
    public void Single_Source_Capped_At_Medium()
    {
        // 用户钦定: 不能只看一家 — 单来源即使高分也封顶 0.65:
        var one = new List<EvidenceItem> { Ev("a.com", 1.0, 1.0) };
        var s = EvidenceScorer.Score(one);
        Assert.True(s <= EvidenceScorer.SingleSourceCap + 0.0001);
        Assert.Equal("medium", EvidenceScorer.GradeOf(s));
    }

    [Fact]
    public void Two_Sources_Can_Reach_High()
    {
        var two = new List<EvidenceItem> { Ev("a.com", 0.9, 0.9), Ev("b.org", 0.9, 0.9) };
        Assert.Equal("high", EvidenceScorer.GradeOf(EvidenceScorer.Score(two)));
    }

    [Fact]
    public void No_Evidence_Scores_None()
    {
        Assert.Equal(0.0, EvidenceScorer.Score(Array.Empty<EvidenceItem>()));
        Assert.Equal("none", EvidenceScorer.GradeOf(0));
    }

    // ── ThinkMemory (RAG 联想) ──
    private static float[] Vec(params float[] xs) => xs;

    [Fact]
    public void Recall_By_Similarity_Threshold()
    {
        var tm = new ThinkMemory();
        tm.Write(new ThinkRecord { QuestionEmbedding = Vec(1, 0, 0), Refs = { "https://a.com" }, RefConfidences = { 0.8 }, AvgConfidence = 0.8 });
        tm.Write(new ThinkRecord { QuestionEmbedding = Vec(0, 1, 0), Refs = { "https://b.com" }, RefConfidences = { 0.9 }, AvgConfidence = 0.9 });
        var hits = tm.Recall(Vec(0.95f, 0.05f, 0));
        Assert.Single(hits); // 第二条正交不命中
        Assert.Contains("https://a.com", hits[0].PreferredRefs);
    }

    [Fact]
    public void PreferredRefs_Ordered_By_Historical_Confidence()
    {
        // 用户钦定: 链接过多时凭 RAG 偏好优先阅览历史高置信度链接:
        var tm = new ThinkMemory();
        tm.Write(new ThinkRecord
        {
            QuestionEmbedding = Vec(1, 0),
            Refs = { "https://low.com", "https://high.com" },
            RefConfidences = { 0.3, 0.95 },
            AvgConfidence = 0.625,
        });
        var hits = tm.Recall(Vec(1, 0));
        Assert.Equal("https://high.com", hits[0].PreferredRefs[0]);
    }

    [Fact]
    public void Citation_Boost_Slight_And_Capped()
    {
        // 用户钦定: 被引用后稍微提升其置信度 (+0.05, 上限 1.0):
        var tm = new ThinkMemory();
        var id = tm.Write(new ThinkRecord { QuestionEmbedding = Vec(1, 0), Refs = { "https://x.com" }, RefConfidences = { 0.5 }, AvgConfidence = 0.5 });
        Assert.True(tm.ApplyCitationBoost(id, "https://x.com"));
        Assert.True(tm.ApplyCitationBoost(id, "https://x.com"));
        var rec = tm.Recall(Vec(1, 0))[0].Record;
        Assert.Equal(0.60, rec.RefConfidences[0], 4); // 0.5 + 0.05×2
    }

    [Fact]
    public void Negative_Outcome_Ranked_Lower()
    {
        var tm = new ThinkMemory();
        tm.Write(new ThinkRecord { QuestionEmbedding = Vec(1, 0), Refs = { "n1" }, RefConfidences = { 0.9 }, AvgConfidence = 0.9, Outcome = "negative" });
        tm.Write(new ThinkRecord { QuestionEmbedding = Vec(0.99f, 0.01f), Refs = { "p1" }, RefConfidences = { 0.6 }, AvgConfidence = 0.6, Outcome = "positive" });
        var hits = tm.Recall(Vec(1, 0));
        Assert.True(hits.Count >= 2);
        Assert.Equal("p1", hits[0].Record.Refs[0]); // 正样本排前 (负样本降权 0.5×)
    }

    [Fact]
    public void Decay_After_Days_And_Archive_Candidates()
    {
        var cfg = new ThinkMemoryConfig { DecayAfterDays = 30, DecayAmount = 0.2, ArchiveBelow = 0.3 };
        var tm = new ThinkMemory(cfg);
        var old = DateTime.UtcNow.AddDays(-40);
        var id = tm.Write(new ThinkRecord { QuestionEmbedding = Vec(1, 0), Refs = { "r" }, RefConfidences = { 0.4 }, AvgConfidence = 0.4, CreatedAtUtc = old });
        var n = tm.Decay(DateTime.UtcNow);
        Assert.Equal(1, n);
        Assert.Contains(id, tm.ArchiveCandidates()); // 0.4-0.2=0.2 < 0.3
    }
}
