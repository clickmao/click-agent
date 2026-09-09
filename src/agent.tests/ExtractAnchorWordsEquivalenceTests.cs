using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text;
using Xunit;

namespace agentframework.tests;

/// <summary>R333/R338 (P10): ExtractAnchorWords long-key 零分配重写的语义等价性 — 反射调用 private
/// 新实现 vs 内联旧算法 (Substring 全滑窗 + string 字典), 随机 CJK/ASCII/标点/emoji 混合文本 × 40 断言全等。
/// 旧算法 (v0.15.2-A 版原文): 每位置 3 次 Substring + string 字典; R338 追加 English >7 词/大小写折叠/
/// 7-8 边界用例 (R333 随机语料英文词全 ≤7 字符, 未覆盖 >7 兜底路径)。</summary>
public class ExtractAnchorWordsEquivalenceTests
{
    private static readonly MethodInfo NewMethod = typeof(agent.context.ContextAssembler)
        .GetMethod("ExtractAnchorWords", BindingFlags.NonPublic | BindingFlags.Static)!;

    private static List<string> OldExtractAnchorWords(string content)
    {
        var words = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (System.Text.RegularExpressions.Match m in
                 System.Text.RegularExpressions.Regex.Matches(content, "[A-Za-z]{3,}"))
        {
            var w = m.Value.ToLowerInvariant();
            words[w] = words.GetValueOrDefault(w) + 1;
        }
        for (var len = 2; len <= 4; len++)
        {
            for (var i = 0; i + len <= content.Length; i++)
            {
                if (!char.IsLetter(content[i]) || content[i] < 0x4E00 || content[i] > 0x9FFF)
                    continue;
                var w = content.Substring(i, len);
                words[w] = words.GetValueOrDefault(w) + 1;
            }
        }
        return words.Where(kv => kv.Value >= 2)
            .OrderByDescending(kv => kv.Value)
            .Take(8)
            .Select(kv => kv.Key)
            .ToList();
    }

    private static List<string> NewExtractAnchorWords(string content)
        => (List<string>)NewMethod.Invoke(null, new object[] { content })!;

    [Theory]
    [InlineData("苹果苹果香蕉 苹果 banana 香蕉 Apple")]
    [InlineData("这是一个测试这是一个测试测试测试")]
    [InlineData("hello world hello again world world")]
    [InlineData("")]
    [InlineData("a")]
    [InlineData("中")]
    [InlineData("中a英b文c混d排e")]
    [InlineData("重复词重复词不重复单次词")]
    [InlineData("abcdefghij abcdefghij elephant elephant cat cat")]   // >7 重复 + ≤7 同 count 交错序
    [InlineData("dog cat dog elephant bird bird")]                     // 短长混合首见序
    [InlineData("abcdefg abcdefg abcdefgh abcdefgh")]                  // 7/8 边界同 count 保首见序
    [InlineData("AbcdefghIJ AbcdefghIJ AbcDefghij abc ABC")]           // >7 大小写折叠 + 短词折叠
    [InlineData("AbcdefG abcdefgh AbcdefG abcdefgh")]                // 7 大写折叠(long 键)与 8(string) 交替
    public void Equivalence_KnownSamples(string s)
        => Assert.Equal(OldExtractAnchorWords(s), NewExtractAnchorWords(s));

    [Fact]
    public void Equivalence_RandomMixedCorpus_40Rounds()
    {
        var rng = new Random(20260910);
        var pool = new[]
        {
            "苹果", "香蕉", "测试", "系统", "代码", "优化", "压缩", "锚点", "内存", "性能",
            "hello", "world", "anchor", "system", "memory", "test",
            "中", "文", "A", "b", "C", "d", " ", " ", "\n", ",", "。", "!", "?", "123",
            "😀", "中英mixed混排", "短", "超长词汇表词汇表词汇表词汇表",
        };
        for (var round = 0; round < 40; round++)
        {
            var sb = new StringBuilder();
            var n = rng.Next(1, 400);
            for (var i = 0; i < n; i++)
                sb.Append(pool[rng.Next(pool.Length)]);
            var s = sb.ToString();
            var oldR = OldExtractAnchorWords(s);
            var newR = NewExtractAnchorWords(s);
            Assert.True(oldR.SequenceEqual(newR), $"round {round} len={s.Length}: old=[{string.Join(",", oldR)}] new=[{string.Join(",", newR)}] text={s[..Math.Min(80, s.Length)]}");
        }
    }

    [Fact]
    public void NewImpl_ProducesExpectedTopWords()
    {
        // 高频 2 字词应稳定进 Top8 (新实现解码正确性锚定)
        var anchors = NewExtractAnchorWords("苹果苹果苹果 苹果 香蕉香蕉香蕉 系统系统 系统 内存内存");
        Assert.Contains("苹果", anchors);
        Assert.Contains("香蕉", anchors);
        Assert.Contains("系统", anchors);
        Assert.All(anchors, a => Assert.False(string.IsNullOrEmpty(a)));
    }
}
