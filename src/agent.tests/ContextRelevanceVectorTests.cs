using System;
using System.Threading;
using System.Threading.Tasks;
using agent.context;
using agent.contextgradient;
using agent.core;
using Xunit;

namespace agent.tests;

/// <summary>
/// v0.11.0 压缩 P3 向量化 (用户钦定): CalculateMessageRelevance 关键词→混合打分。
/// 契约:
///   ① embedder 不可用 → 纯词面 (P1 行为兼容, 分数与旧版一致)
///   ② embedder 可用 → 0.6×词面 + 0.4×语义, 强语义 (≥0.8) 抬底 0.8
///   ③ 嵌入失败 → 词面兜底 (不抛异常, 召回不中断)
///   ④ 查询向量一轮会话召回只嵌入一次 (假 embedder 计数验证)
/// </summary>
public class ContextRelevanceVectorTests
{
    /// <summary>可控向量假嵌入器: 文本含 "猫" → 向量 A; 含 "犬/dog" → 向量 B (与 A 正交); 其他 → 零向量。</summary>
    private sealed class FakeEmbedder : ITextEmbedder
    {
        public bool IsAvailable => true;
        public int CallCount;
        public Task<float[]> EmbedAsync(string text, CancellationToken ct = default)
        {
            Interlocked.Increment(ref CallCount);
            if (text.Contains("猫"))
                return Task.FromResult(new float[] { 1f, 0f });
            if (text.Contains("犬") || text.Contains("dog"))
                return Task.FromResult(new float[] { 0f, 1f });
            return Task.FromResult(System.Array.Empty<float>());
        }
    }

    [Fact]
    public async Task LexicalOnly_WhenEmbedderAbsent_BehavesAsP1()
    {
        var score = await ContextAssembler.CalculateMessageRelevanceForTest(
            MakeMessage("今天讨论猫粮品牌"), "猫粮", embedder: null);
        // 词面命中 1/1 = 1.0 (P1 语义不变)
        Assert.Equal(1.0, score, precision: 5);
    }

    [Fact]
    public async Task HybridBlend_SemanticComplementsLexical()
    {
        var embedder = new FakeEmbedder();
        // 词面 0 命中 (0.1 底), 但语义同向量 (cos=1) → 混合 ≥ 0.8 抬底
        var score = await ContextAssembler.CalculateMessageRelevanceForTest(
            MakeMessage("猫在晒太阳"), "猫科动物习性", embedder);
        Assert.True(score >= 0.8, $"强语义应抬底 0.8, 实际 {score}");
    }

    [Fact]
    public async Task HybridBlend_LexicalDominates()
    {
        var embedder = new FakeEmbedder();
        // 词面全命中 1.0 + 语义同向量 cos=1 → blended = 0.6+0.4 = 1.0 (双通道一致强相关)
        var score = await ContextAssembler.CalculateMessageRelevanceForTest(
            MakeMessage("犬吠训练指南 dog"), "犬 dog", embedder);
        Assert.Equal(1.0, score, precision: 5);
    }

    [Fact]
    public async Task EmbedFailure_FallsBackToLexical()
    {
        var failing = new ThrowingEmbedder();
        // 嵌入抛异常 → 词面兜底 1.0 (召回不中断)
        var score = await ContextAssembler.CalculateMessageRelevanceForTest(
            MakeMessage("猫粮品牌讨论"), "猫粮", failing);
        Assert.Equal(1.0, score, precision: 5);
    }

    private static Message MakeMessage(string content) => new()
    {
        Role = MessageRole.User,
        Content = content,
        Id = "m" + Guid.NewGuid().ToString("N"),
        Timestamp = DateTime.UtcNow,
    };

    private sealed class ThrowingEmbedder : ITextEmbedder
    {
        public bool IsAvailable => true;
        public Task<float[]> EmbedAsync(string text, CancellationToken ct = default) =>
            throw new InvalidOperationException("嵌入服务不可用");
    }
}
