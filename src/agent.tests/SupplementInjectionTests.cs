using System.Collections.Generic;
using agent.rag;
using agent.r1;
using Xunit;

namespace agent.tests;

/// <summary>
/// 「用户补充在合理时机插入」的机检：台账（去重/阈值拒收/一次性消费/收割）+ 尾部块渲染（缓存安全）。
/// 断言只依赖真实产品行为，不新增器具层。
/// </summary>
public sealed class SupplementInjectionTests
{
    private sealed class FixedScorer : IRerankScorer
    {
        private readonly double _score;

        public FixedScorer(double score) => _score = score;

        public double Score(string query, string document, double coarseScore) => _score;
    }

    [Fact]
    public void Enqueue_Rejects_Blank_And_Duplicates()
    {
        var inbox = new SupplementInbox(new FixedScorer(1.0), 0.05);

        Assert.False(inbox.Enqueue("   "));
        Assert.False(inbox.Enqueue(null));
        Assert.True(inbox.Enqueue("把日志级别调成 warning"));
        Assert.False(inbox.Enqueue("  把日志级别调成 warning  "));
        Assert.Equal(1, inbox.PendingCount);
    }

    [Fact]
    public void BelowThreshold_Is_Not_Injected_And_Stays_Pending()
    {
        var inbox = new SupplementInbox(new FixedScorer(0.01), 0.05);
        Assert.True(inbox.Enqueue("无关的一句话"));

        var picked = inbox.SelectFor("当前步骤文本");

        Assert.Empty(picked);
        Assert.Equal(1, inbox.PendingCount);
        Assert.Equal(0, inbox.ConsumedCount);
    }

    [Fact]
    public void AboveThreshold_Is_Injected_Then_Consumed_Exactly_Once()
    {
        var inbox = new SupplementInbox(new FixedScorer(1.0), 0.05);
        Assert.True(inbox.Enqueue("补充甲"));
        Assert.True(inbox.Enqueue("补充乙"));

        var first = inbox.SelectFor("当前步骤文本", 1);
        Assert.Single(first);
        Assert.Equal(1, inbox.MarkConsumed(first));

        var second = inbox.SelectFor("当前步骤文本", 2);
        Assert.Single(second);
        Assert.NotEqual(first[0], second[0]);

        inbox.MarkConsumed(second);
        Assert.Equal(0, inbox.PendingCount);
        Assert.Equal(2, inbox.ConsumedCount);
        Assert.Empty(inbox.SelectFor("当前步骤文本"));
    }

    [Fact]
    public void Harvest_Pulls_New_Items_From_Source_Only_Once()
    {
        var source = new List<string> { "第一条" };
        var inbox = new SupplementInbox(new FixedScorer(1.0), 0.05, () => source);

        Assert.Equal(1, inbox.Harvest());
        Assert.Equal(0, inbox.Harvest());
        Assert.Equal(1, inbox.PendingCount);

        source.Add("第二条");
        Assert.Equal(1, inbox.Harvest());
        Assert.Equal(2, inbox.PendingCount);
    }

    [Fact]
    public void Harvest_Survives_Missing_Drop_File()
    {
        var inbox = new SupplementInbox(
            new FixedScorer(1.0), 0.05, SupplementInbox.DropFileSource("/tmp/definitely-absent-supplements.txt"));

        Assert.Equal(0, inbox.Harvest());
        Assert.Equal(0, inbox.PendingCount);
    }

    [Fact]
    public void SupplementBlock_Renders_At_Tail_And_Is_Empty_When_Nothing_To_Inject()
    {
        Assert.Equal(string.Empty, SupplementBlock.Render(null));
        Assert.Equal(string.Empty, SupplementBlock.Render(new List<string>()));
        Assert.Equal(string.Empty, SupplementBlock.Render(new List<string> { "  " }));

        var block = SupplementBlock.Render(new List<string> { " 把日志级别调成 warning " });

        Assert.StartsWith("\n\n" + SupplementBlock.Header, block);
        Assert.Contains("- 把日志级别调成 warning", block);
        Assert.EndsWith(SupplementBlock.Footer + "\n", block);
        Assert.DoesNotContain("  \n", block);
    }

    [Fact]
    public void ZeroBehavior_When_No_Supplement_Configured()
    {
        var inbox = new SupplementInbox(new FixedScorer(1.0), 0.05);

        Assert.Empty(inbox.SelectFor("步骤"));
        Assert.Equal(0, inbox.Harvest());
        Assert.Equal(0, inbox.MarkConsumed(null));
        Assert.Equal(0, inbox.MarkConsumed(new List<string>()));
    }
}
