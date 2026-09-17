// v0.22.0 exp9 D4+D5 机检: 本地先行 (无依赖本地节点与远程生成真并行) + 计划事件出站。
//
// 断言原则 (对齐用户审计口径): 每条断言绑定**组件真实行为**, 不用"看着像"的弱断言。
//  - D4 正向: 无依赖本地节点在"远程产物尚不存在"时即完成 (RemoteText == null ⇒ 真先行)
//  - D4 负向: 计划无此类节点时 StartLocalFirst 必须返回 null (不许假装先行)
//  - D4 幂等: 先行批次的结果被复用, 节点**不重复执行** (以 plan.node 事件条数计 = 1)
//  - D4 重叠: overlap_ms > 0 且 <= min(本地先行耗时, 远程窗口) (几何可证)
//  - D5 正向: plan.created / plan.node / plan.finished 三事件按序出站, 载荷含位置与耗时
//  - D5 兜底: 事件出口抛异常**不得**打断计划 (计划仍返回 run, 节点仍 Completed)
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using agent.intent;
using Xunit;
namespace agent.tests;

public class PlanLocalFirstTests
{
    // ── D4: 判定层 ────────────────────────────────────────────────────────────

    [Fact]
    public void AsksSourceTextOp_双命中为真()
    {
        Assert.True(LocalVerifyNodePlanner.AsksSourceTextOp(
            "用 python 开发一个贪吃蛇, 并统计我这段需求描述的字数"));
        Assert.True(LocalVerifyNodePlanner.AsksSourceTextOp(
            "帮我写个脚本, 顺便统计需求里的关键词"));
    }

    [Theory]
    [InlineData("用 python 开发一个贪吃蛇")]                  // 无动作词
    [InlineData("统计这个项目有多少行代码")]                   // 有动作词, 无"原文"对象词 → 属生成内容, 不该本地先行
    [InlineData("")]
    [InlineData(null)]
    public void AsksSourceTextOp_缺一即否(string? text)
    {
        Assert.False(LocalVerifyNodePlanner.AsksSourceTextOp(text));
    }

    [Fact]
    public void 路由_原文文本处理单列为无依赖本地节点_生成节点不吸收()
    {
        const string src = "用 python 开发一个贪吃蛇, 并统计我这段需求描述的字数";
        var plan = RoutedPlanBuilder.Build(src, Array.Empty<IntentDecomposer.SubTask>());

        var localText = plan.Nodes.SingleOrDefault(n =>
            n.Intent == PlanNodeIntents.TextProcessing && n.DependsOn.Count == 0);
        Assert.NotNull(localText);
        Assert.Equal(NodeExecutionLocation.Local, localText!.Location);
        Assert.Equal(LocalExecutorRegistry.TextProcess, localText.LocalExecutorId);
        Assert.Equal(0, localText.Level);

        // 生成节点不因"统计"二字被 Hybrid 吸收 (Hybrid 的第二段输入是生成内容, 目标不同)
        Assert.DoesNotContain(plan.Nodes, n =>
            n.Location == NodeExecutionLocation.Hybrid && n.Text.Contains("贪吃蛇", StringComparison.Ordinal));

        // 无依赖本地节点必须被登记为"可本地执行"
        Assert.Contains(localText.Id, plan.LocalExecutableNodeIds);
    }

    [Fact]
    public void 路由_无原文文本处理需求时_不追加无依赖本地节点()
    {
        var plan = RoutedPlanBuilder.Build(
            "用 python 开发一个贪吃蛇", Array.Empty<IntentDecomposer.SubTask>());
        Assert.DoesNotContain(plan.Nodes, n => n.DependsOn.Count == 0 && n.RunsLocally);
    }

    // ── D4: 执行层 ────────────────────────────────────────────────────────────

    [Fact]
    public async Task 本地先行_产物未就绪时即完成且读取的是本轮原文()
    {
        const string src = "用 python 开发一个贪吃蛇, 并统计我这段需求描述的字数";
        var plan = RoutedPlanBuilder.Build(src, Array.Empty<IntentDecomposer.SubTask>());
        var runner = new PlanRunner();
        var sink = new RecordingSink();
        var runnerWithSink = new PlanRunner(events: sink);
        var ctx = PlanRunner.NewContext(sessionId: "s-local-first", sourceText: src);

        var batch = runnerWithSink.StartLocalFirst(plan, ctx);
        Assert.NotNull(batch);

        var nodeId = batch!.NodeIds.Single();
        await batch.Pending;   // 远程产物**此时根本不存在** (ctx.RemoteText == null, 产物台账为空)

        Assert.Null(ctx.RemoteText);
        Assert.True(batch.Outcomes.TryGetValue(nodeId, out var outcome));
        Assert.Equal(PlanNodeState.Completed, outcome!.State);
        // 真读了本轮原文: 统计字符数 == 原文长度
        Assert.Contains(src.Length.ToString(), outcome.Detail, StringComparison.Ordinal);

        // 未知会"先行"的节点: 只有无依赖本地节点在册
        Assert.All(batch.NodeIds, id =>
            Assert.Equal(string.Empty, plan.Nodes.Single(n => n.Id == id).DependsOn.FirstOrDefault() ?? string.Empty));
        _ = runner; // 无 sink 的 runner 不参与本断言 (保留作对照)
    }

    [Fact]
    public void 本地先行_无可先行节点时必须返回null()
    {
        var plan = RoutedPlanBuilder.Build(
            "用 python 开发一个贪吃蛇", Array.Empty<IntentDecomposer.SubTask>());
        var runner = new PlanRunner();
        var ctx = PlanRunner.NewContext(sessionId: "s-none", sourceText: "用 python 开发一个贪吃蛇");

        Assert.Null(runner.StartLocalFirst(plan, ctx));
    }

    [Fact]
    public async Task 本地先行结果被复用_节点不重复执行()
    {
        const string src = "用 python 开发一个贪吃蛇, 并统计我这段需求描述的字数";
        var plan = RoutedPlanBuilder.Build(src, Array.Empty<IntentDecomposer.SubTask>());
        var sink = new RecordingSink();
        var runner = new PlanRunner(events: sink);
        var ctx = PlanRunner.NewContext(sessionId: "s-idem", sourceText: src);

        var batch = runner.StartLocalFirst(plan, ctx);
        Assert.NotNull(batch);
        long startUs = Monotonic.NowUs();

        // 远程产物就绪 (窗口中点) → 跑整张计划
        var run = await runner.RunAsync(plan, ctx, CancellationToken.None, batch,
            new RemoteWindow(startUs, Monotonic.NowUs() + 5000));

        Assert.NotNull(run);
        var localTextId = batch!.NodeIds.Single();
        // 幂等: 该节点只出一次 plan.node 事件 ⇒ 只执行一次
        Assert.Equal(1, sink.CountOf(PlanEvents.Node, localTextId));
        Assert.Equal(1, run!.Outcomes.Count(o => o.NodeId == localTextId));
        Assert.Equal(PlanNodeState.Completed, run.Outcomes.Single(o => o.NodeId == localTextId).State);
    }

    [Fact]
    public async Task 重叠ms_大于零且不超过本地先行耗时()
    {
        const string src = "用 python 开发一个贪吃蛇, 并统计我这段需求描述的字数";
        var plan = RoutedPlanBuilder.Build(src, Array.Empty<IntentDecomposer.SubTask>());
        var runner = new PlanRunner();
        var ctx = PlanRunner.NewContext(sourceText: src);

        long t0 = Monotonic.NowUs();
        var batch = runner.StartLocalFirst(plan, ctx);
        Assert.NotNull(batch);
        await batch!.Pending;

        // 远程窗口: 起点=计划构建时刻, 终点=产物就绪 (刻意晚于本地先行结束 → 几何上必重叠)
        var run = await runner.RunAsync(plan, ctx, CancellationToken.None, batch,
            new RemoteWindow(t0, Monotonic.NowUs() + 5000));

        var kpi = run!.Kpi;
        Assert.NotNull(kpi);
        Assert.Equal(1, kpi!.LocalFirstNodes);
        Assert.True(kpi.OverlapUs > 0, $"overlap_us 应为正 (亚毫秒本地节点用 µs), 实得 {kpi.OverlapUs}");
        Assert.True(kpi.OverlapUs <= Math.Max(1, kpi.LocalFirstUs),
            $"overlap_us({kpi.OverlapUs}) 不得超过本地先行耗时({kpi.LocalFirstUs}) µs");
        Assert.True(kpi.RemoteWaitUs >= kpi.OverlapUs);
        Assert.Equal(0, kpi.LocalTokens);
    }

    [Fact]
    public async Task 远程窗口缺席时_重叠为0且不报错()
    {
        const string src = "用 python 开发一个贪吃蛇, 并统计我这段需求描述的字数";
        var plan = RoutedPlanBuilder.Build(src, Array.Empty<IntentDecomposer.SubTask>());
        var runner = new PlanRunner();
        var ctx = PlanRunner.NewContext(sourceText: src);

        var batch = runner.StartLocalFirst(plan, ctx);
        var run = await runner.RunAsync(plan, ctx, CancellationToken.None, batch, remoteWindow: null);

        Assert.Equal(0, run!.Kpi!.OverlapUs);
        Assert.Equal(0, run.Kpi.RemoteWaitUs);
    }

    // ── D5: 事件出站 ─────────────────────────────────────────────────────────

    [Fact]
    public async Task 前端事件_创建节点完成三事件按序出站且载荷含位置()
    {
        const string src = "用 python 开发一个贪吃蛇, 并统计我这段需求描述的字数";
        var plan = RoutedPlanBuilder.Build(src, Array.Empty<IntentDecomposer.SubTask>());
        var sink = new RecordingSink();
        var runner = new PlanRunner(events: sink);
        var ctx = PlanRunner.NewContext(sessionId: "s-events", sourceText: src);

        await runner.AnnounceAsync(plan);
        var localFirst = runner.StartLocalFirst(plan, ctx);
        Assert.NotNull(localFirst); // 该请求含"统计我这段…字数" ⇒ 必有可先行的本地节点
        var run = await runner.RunAsync(plan, ctx, default, localFirst);

        Assert.Equal(1, sink.CountOf(PlanEvents.Created));
        // 一节点一事件 (无重复)
        Assert.Equal(plan.Nodes.Count, sink.CountOf(PlanEvents.Node));
        Assert.Equal(1, sink.CountOf(PlanEvents.Finished));

        var created = sink.Payloads(PlanEvents.Created).Single();
        using var doc = JsonDocument.Parse(created);
        Assert.Equal(plan.PlanId, doc.RootElement.GetProperty("plan_id").GetString());
        Assert.Equal(plan.Nodes.Count, doc.RootElement.GetProperty("nodes_total").GetInt32());
        var nodes = doc.RootElement.GetProperty("nodes");
        Assert.Equal(plan.Nodes.Count, nodes.GetArrayLength());
        // 每个节点都带位置 (前端要"哪步本地/哪步远程")
        Assert.All(nodes.EnumerateArray().ToList(), n =>
            Assert.False(string.IsNullOrEmpty(n.GetProperty("location").GetString())));

        var finished = sink.Payloads(PlanEvents.Finished).Single();
        using var fd = JsonDocument.Parse(finished);
        Assert.True(fd.RootElement.TryGetProperty("overlap_us", out var ov), "plan.finished 必须带 overlap_us");
        Assert.True(ov.GetInt64() >= 0);
        // D4: 真有可先行节点 ⇒ 事件里必须自认 local_first=true 且带节点数 (前端据此显示"哪几步先跑")
        Assert.True(fd.RootElement.GetProperty("local_first").GetBoolean());
        Assert.Equal(1, fd.RootElement.GetProperty("local_first_nodes").GetInt32());
    }

    [Fact]
    public async Task 事件出口故障_不得打断计划()
    {
        const string src = "用 python 开发一个贪吃蛇, 并统计我这段需求描述的字数";
        var plan = RoutedPlanBuilder.Build(src, Array.Empty<IntentDecomposer.SubTask>());
        var runner = new PlanRunner(events: new ThrowingSink());
        var ctx = PlanRunner.NewContext(sourceText: src);

        var run = await runner.RunAsync(plan, ctx);

        Assert.NotNull(run);
        Assert.Equal(plan.Nodes.Count, run!.Outcomes.Count);
        Assert.All(run.Outcomes, o => Assert.Equal(PlanNodeState.Completed, o.State));
    }

    // ── 测试替身 ─────────────────────────────────────────────────────────────

    private sealed class RecordingSink : IPlanEventSink
    {
        private readonly ConcurrentQueue<(string Event, string Payload)> _events = new();
        public Task EmitAsync(string @event, string payloadJson, CancellationToken ct = default)
        {
            _events.Enqueue((@event, payloadJson));
            return Task.CompletedTask;
        }
        public int CountOf(string @event) => _events.Count(e => e.Event == @event);
        public int CountOf(string @event, string nodeId) =>
            _events.Count(e => e.Event == @event && e.Payload.Contains(nodeId, StringComparison.Ordinal));
        public IEnumerable<string> Payloads(string @event) =>
            _events.Where(e => e.Event == @event).Select(e => e.Payload).ToList();
    }

    private sealed class ThrowingSink : IPlanEventSink
    {
        public Task EmitAsync(string @event, string payloadJson, CancellationToken ct = default) =>
            throw new InvalidOperationException("sink down");
    }
}
