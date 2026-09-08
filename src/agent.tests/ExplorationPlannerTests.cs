using agent.exploration;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.13.0 M1 — 渐进式探索规划器单测。
/// 覆盖用户钦定语义: ①上下文内 URL 优先于上下文外目录 ②per-source 最大步数预算 ③全局预算 ④去重 ⑤发现链。
/// </summary>
public class ExplorationPlannerTests
{
    [Fact]
    public void ContextUrl_Outranks_ExternalDirectory()
    {
        // 用户例: 从上下文探索到网页链接 > 上下文外的指定目录
        var p = new ExplorationPlanner();
        p.Seed(ExploreSourceKind.Directory, "/data/docs", fromContext: false);
        p.Seed(ExploreSourceKind.Url, "https://example.com/spec", fromContext: true);
        var first = p.TryDequeueNext()!;
        Assert.Equal(ExploreSourceKind.Url, first.Kind);
        Assert.True(first.FromContext);
    }

    [Fact]
    public void PerSourceBudget_Stops_Progressive_Dive()
    {
        var cfg = new ExplorationConfig { MaxStepsPerUrl = 2, MaxTotalSteps = 99 };
        var p = new ExplorationPlanner(cfg);
        p.Seed(ExploreSourceKind.Url, "https://example.com/a", fromContext: true);
        var n1 = p.TryDequeueNext();
        Assert.NotNull(n1);
        p.Record(new ExploreStepResult { Ok = true, Kind = ExploreSourceKind.Url, Ref = n1!.Ref }, n1);
        p.Requeue(n1); // 第2步
        var n2 = p.TryDequeueNext();
        Assert.NotNull(n2);
        p.Record(new ExploreStepResult { Ok = true, Kind = ExploreSourceKind.Url, Ref = n2!.Ref }, n2);
        p.Requeue(n2); // 第3次 → 超预算, 不得再出
        Assert.Null(p.TryDequeueNext());
    }

    [Fact]
    public void GlobalBudget_Exhausts()
    {
        var cfg = new ExplorationConfig { MaxTotalSteps = 2, MaxStepsPerUrl = 9 };
        var p = new ExplorationPlanner(cfg);
        p.Seed(ExploreSourceKind.Url, "https://e1.com", fromContext: true);
        p.Seed(ExploreSourceKind.Url, "https://e2.com", fromContext: true);
        p.Seed(ExploreSourceKind.Url, "https://e3.com", fromContext: true);
        Assert.NotNull(p.TryDequeueNext());
        Assert.NotNull(p.TryDequeueNext());
        // 只允许 2 步:
        p.Record(new ExploreStepResult { Ok = true }, new ExploreNode());
        p.Record(new ExploreStepResult { Ok = true }, new ExploreNode());
        Assert.True(p.BudgetExhausted);
        Assert.Null(p.TryDequeueNext());
    }

    [Fact]
    public void Dedup_ByRef_IgnoreCase_TrailingSlash()
    {
        var p = new ExplorationPlanner();
        p.Seed(ExploreSourceKind.Url, "https://Example.com/x/", fromContext: true);
        p.Seed(ExploreSourceKind.Url, "https://example.com/x", fromContext: true);
        Assert.Single(p.PendingSnapshot);
    }

    [Fact]
    public void DiscoveryChain_Enqueues_New_Unique_Sources()
    {
        var p = new ExplorationPlanner();
        p.Seed(ExploreSourceKind.ContextBlock, "snippet-1", fromContext: true);
        var node = p.TryDequeueNext()!;
        var step = new ExploreStepResult { Ok = true, Kind = ExploreSourceKind.ContextBlock, Ref = node.Ref };
        step.Discovered.Add(new ExploreNode { Kind = ExploreSourceKind.Url, Ref = "https://found.example", FromContext = true });
        step.Discovered.Add(new ExploreNode { Kind = ExploreSourceKind.Url, Ref = "https://found.example", FromContext = true }); // 重复
        var enq = p.Record(step, node);
        Assert.Single(enq);
    }

    [Fact]
    public void Requeue_DepthPenalty_Keeps_Breadth_First_Tendency()
    {
        var cfg = new ExplorationConfig { MaxStepsPerUrl = 5 };
        var p = new ExplorationPlanner(cfg);
        p.Seed(ExploreSourceKind.Url, "https://deep.example", fromContext: true);
        p.Seed(ExploreSourceKind.Url, "https://fresh.example", fromContext: true);
        var deep = p.TryDequeueNext()!;
        Assert.Equal("https://deep.example", deep.Ref); // 同优先级 FIFO
        p.Record(new ExploreStepResult { Ok = true }, deep);
        p.Requeue(deep); // deep 加罚
        var next = p.TryDequeueNext()!;
        Assert.Equal("https://fresh.example", next.Ref); // 新源先行 (广度优先)
    }

    [Fact]
    public void External_Priority_Penalty_Applies()
    {
        var cfg = new ExplorationConfig();
        int inCtx = cfg.GetPriority(ExploreSourceKind.Url, fromContext: true);
        int ext = cfg.GetPriority(ExploreSourceKind.Url, fromContext: false);
        Assert.True(ext > inCtx, $"external({ext}) 应低于上下文内({inCtx})优先级");
    }
}
