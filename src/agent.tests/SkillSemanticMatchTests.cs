using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using agent.skills;
using Xunit;

namespace agent.tests;

/// <summary>
/// v0.10.0 Skill P3 语义匹配 (bge): TriggerMatcher 语义层契约。
///   ① 嵌入器注入后, 词面全未命中但语义近邻 (cos ≥ 阈值) → 疑似命中
///   ② 嵌入器不可用 (IsAvailable=false) → 行为与原三级匹配完全一致 (兼容)
///   ③ 语义命中不高于关键词命中 (裁决: precision 语义 < 关键词)
/// </summary>
public class SkillSemanticMatchTests
{
    private sealed class FakeEmbedder : agent.contextgradient.ITextEmbedder
    {
        private readonly Func<string, float[]> _embed;
        public bool IsAvailable { get; set; } = true;
        public FakeEmbedder(Func<string, float[]> embed) => _embed = embed;
        public Task<float[]> EmbedAsync(string text, CancellationToken ct = default)
            => Task.FromResult(IsAvailable ? _embed(text) : throw new InvalidOperationException("unavailable"));
    }

    private static SkillDefinition NewSkill(string name, string domain,
        List<string>? keywords = null, List<string>? domainWords = null) => new()
    {
        SkillId = name.ToLowerInvariant(),
        Name = name,
        Domain = domain,
        Keywords = keywords ?? new List<string>(),
        DomainWords = domainWords ?? new List<string>(),
    };

    [Fact]
    public void Semantic_Near_Input_Triggers_Suspected()
    {
        // "k8s 集群扩容" 与 skill "容器编排 Kubernetes 部署, k8s" 语义近邻 (同向向量)
        var embed = new FakeEmbedder(text =>
            text.Contains("k8s") || text.Contains("Kubernetes") || text.Contains("容器")
                ? new float[] { 1, 0, 0 }
                : new float[] { 0, 1, 0 });
        var matcher = new TriggerMatcher(embed, suspectedTrigger: true, semanticThreshold: 0.45f);

        var skill = NewSkill("容器编排", "Kubernetes 部署", keywords: new() { "kubernetes" });
        var hits = matcher.Match("k8s 集群怎么扩容", new List<SkillDefinition> { skill });

        Assert.Single(hits);
        Assert.Equal(1, hits[0].Level);          // 语义命中 = 疑似级
        Assert.True(hits[0].Precision >= 0.30);  // 语义 precision ≥ 领域词下限
    }

    [Fact]
    public void Semantic_Far_Input_Does_Not_Trigger()
    {
        // "今天天气" 与容器编排语义正交 (垂直向量 cos=0) → 不命中
        var embed = new FakeEmbedder(text =>
            text.Contains("k8s") || text.Contains("Kubernetes")
                ? new float[] { 1, 0 }
                : new float[] { 0, 1 });
        var matcher = new TriggerMatcher(embed, semanticThreshold: 0.45f);

        var skill = NewSkill("容器编排", "Kubernetes 部署", keywords: new() { "kubernetes" });
        var hits = matcher.Match("今天天气怎么样", new List<SkillDefinition> { skill });

        Assert.Empty(hits);
    }

    [Fact]
    public void Unavailable_Embedder_Falls_Back_To_Lexical()
    {
        // 嵌入器不可用 → 纯词面匹配, 行为与原 TriggerMatcher 一致
        var embed = new FakeEmbedder(_ => Array.Empty<float>()) { IsAvailable = false };
        var matcher = new TriggerMatcher(embed, suspectedTrigger: true);

        var skill = NewSkill("容器编排", "Kubernetes 部署", keywords: new() { "kubernetes" });
        var hits = matcher.Match("k8s 集群扩容", new List<SkillDefinition> { skill });

        Assert.Empty(hits); // 词面未命中 (k8s ≠ kubernetes) 且语义不可用 → 空
    }

    [Fact]
    public void Keyword_Hit_Beats_Semantic_Hit()
    {
        // 关键词精确命中 (level 2) 与语义命中 (level 1) 同 skill → 词面优先级保留
        var embed = new FakeEmbedder(_ => new float[] { 1, 0 });
        var matcher = new TriggerMatcher(embed, semanticThreshold: 0.45f);

        var skill = NewSkill("容器编排", "Kubernetes 部署", keywords: new() { "kubernetes" });
        var hits = matcher.Match("kubernetes 集群扩容", new List<SkillDefinition> { skill });

        Assert.Single(hits);
        Assert.Equal(2, hits[0].Level); // 关键词命中 level=2
        Assert.Equal(0.6, hits[0].Precision, 5);
    }
}
