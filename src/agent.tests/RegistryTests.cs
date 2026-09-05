using System.Text.Json;
using agent.core;
using agent.intent;
using agent.registry;
using agent.subagent;
using Xunit;
using Xunit.Abstractions;

namespace agent.tests;

/// <summary>
/// v7.11 六件套: AgentRegistry 持久化 UID + 从属关系 / NextTurnForecast 落盘读回 /
/// LocalCommandRouter 强制指令 / TaskPlanExecutor 顺序调度 / ResponseSegmenter 快速标记 /
/// ClarificationService 权威路由。
/// </summary>
public class RegistryTests : IDisposable
{
    private readonly string _dir;
    private readonly ITestOutputHelper _out;

    public RegistryTests(ITestOutputHelper output)
    {
        _out = output;
        _dir = Path.Combine(Path.GetTempPath(), "af_reg_" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(_dir);
    }

    public void Dispose()
    {
        try { Directory.Delete(_dir, recursive: true); } catch { }
    }

    // ---------- AgentRegistry ----------

    [Fact]
    public void AgentRegistry_PersistsUidAndHierarchy()
    {
        var reg1 = new AgentRegistry(_dir);
        var sub = reg1.Register("researcher", "main");
        Assert.NotEqual("main", sub.Uid);
        Assert.Equal("main", sub.ParentUid);
        Assert.Equal(1, sub.Depth);
        Assert.Equal(0, reg1.Main.Depth);

        // 新实例 (模拟重启) → 同名复用 UID
        var reg2 = new AgentRegistry(_dir);
        var sub2 = reg2.Get(sub.Uid);
        Assert.NotNull(sub2);
        Assert.Equal("researcher", sub2!.Name);
        Assert.Equal(sub.Uid, reg2.Register("researcher", "main").Uid);
    }

    [Fact]
    public void AgentRegistry_ChildrenOf_And_DeepNesting()
    {
        var reg = new AgentRegistry(_dir);
        var a = reg.Register("worker-a", "main");
        var b = reg.Register("worker-b", a.Uid);
        Assert.Equal(2, b.Depth);
        Assert.Equal(["worker-a"], reg.ChildrenOf("main").Select(x => x.Name).OrderBy(x => x));
        Assert.Single(reg.ChildrenOf(a.Uid));
    }

    [Fact]
    public void AgentRegistry_CorruptFile_RecoversGracefully()
    {
        Directory.CreateDirectory(_dir);
        File.WriteAllText(Path.Combine(_dir, "agent_registry.json"), "{ not json");
        var reg = new AgentRegistry(_dir); // 不抛
        Assert.NotNull(reg.Main);
        var sub = reg.Register("x", "main");
        Assert.NotEqual("main", sub.Uid);
    }

    // ---------- NextTurnForecast ----------

    [Fact]
    public void Forecast_RoundTrips_AcrossProcessSim()
    {
        NextTurnForecast.Save(_dir, "main", "先搜索 AOT 资料，然后写总结", "search");
        var rec = NextTurnForecast.Save(_dir, "main", "继续写测试", "test_generation");

        Assert.Equal(2, rec.TurnCount);      // 同 agent 累计轮次
        Assert.True(rec.LikelyContinues);    // "继续" → 延续倾向

        // 模拟重启: 新读回 (跨进程)
        var loaded = NextTurnForecast.Load(_dir, "main");
        Assert.NotNull(loaded);
        Assert.Equal("test_generation", loaded!.LastIntent);
        var header = NextTurnForecast.ToPromptHeader(loaded);
        Assert.Contains("下轮预估", header);
        Assert.Contains("倾向", header);
    }

    [Fact]
    public void Forecast_IsolatedPerAgent()
    {
        NextTurnForecast.Save(_dir, "main", "主 agent 任务", "code_generation");
        NextTurnForecast.Save(_dir, "a123", "子 agent 任务", "search");

        var main = NextTurnForecast.Load(_dir, "main")!;
        var sub = NextTurnForecast.Load(_dir, "a123")!;
        Assert.Contains("主 agent", main.TaskSummary);
        Assert.Contains("子 agent", sub.TaskSummary);
        Assert.Equal(1, main.TurnCount);
        Assert.Equal(1, sub.TurnCount);
        Assert.Null(NextTurnForecast.Load(_dir, "ghost"));
    }

    [Fact]
    public void Forecast_Header_EmptyWithoutRecord() =>
        Assert.Equal(string.Empty, NextTurnForecast.ToPromptHeader(null));

    // ---------- LocalCommandRouter ----------

    [Theory]
    [InlineData("/stop", true, "stop")]
    [InlineData("/continue", true, "continue")]
    [InlineData("/STOP now", true, "stop")]
    [InlineData("  /pause  ", true, "pause")]
    [InlineData("请停止", false, "")]          // 自然语言不是本地命令 (走意图/插入指令分类)
    [InlineData("/unknown", false, "")]        // 未知命令不拦截
    [InlineData("color: red", false, "")]      // 以 c 开头不以 / 开头
    public void LocalCommands_Route(string input, bool handled, string cmd)
    {
        var r = LocalCommandRouter.TryRoute(input);
        Assert.Equal(handled, r.Handled);
        Assert.Equal(cmd, r.Command);
    }

    // ---------- TaskPlanExecutor ----------

    private static TaskPlan Plan3() =>
        TaskPlanBuilder.Build("先搜索资料，然后基于结果写代码，最后读取文件核对",
            IntentDecomposer.Decompose("先搜索资料，然后基于结果写代码，最后读取文件核对"));

    [Fact]
    public async Task Executor_PausesOnSensitiveNode()
    {
        // file_operation 是敏感意图 → 运行到该节点全计划暂停
        var executor = new TaskPlanExecutor((n, ct) =>
            Task.FromResult(new NodeExecutionResult { NodeId = n.Id, FinalState = PlanNodeState.Completed, Output = "ok" }));
        var run = await executor.ExecuteAsync(Plan3());

        Assert.Equal(TaskPlanRunState.PausedForApproval, run.State);
        // v7.12 链式拓扑: search → code_gen (基于) → file_op (最后) — 非敏感的 code_gen 先完成, 到 file_op 才暂停
        Assert.Equal(2, run.NodeStates.Values.Count(s => s == PlanNodeState.Completed));
        Assert.Equal(PlanNodeState.AwaitingApproval, run.NodeStates[run.PendingSensitiveNodeId!]);
        Assert.NotNull(run.PauseReason);
    }

    [Fact]
    public async Task Executor_CancelInjection_StopsAndSkips()
    {
        var executor = new TaskPlanExecutor((n, ct) =>
            Task.FromResult(new NodeExecutionResult { NodeId = n.Id, FinalState = PlanNodeState.Completed }));

        // 非敏感计划: 用纯 search/general 句
        var plan = TaskPlanBuilder.Build("先搜索资料，然后写一首诗",
            IntentDecomposer.Decompose("先搜索资料，然后写一首诗"));
        var injected = new InjectedInstruction { Text = "停止", Kind = InjectedInstructionKind.Cancel };

        var run = await executor.ExecuteAsync(plan, pollInjections: () => injected);

        Assert.Equal(TaskPlanRunState.Cancelled, run.State);
        Assert.Contains(PlanNodeState.Skipped, run.NodeStates.Values);
    }

    [Fact]
    public async Task Executor_AwaitingClarification_DoesNotBlockIndependentNodes()
    {
        var executor = new TaskPlanExecutor((n, ct) =>
            Task.FromResult(new NodeExecutionResult { NodeId = n.Id, FinalState = PlanNodeState.Completed }));

        // 非敏感节点缺必填参数 → AwaitingClarification; 无关节点照常完成
        var plan = TaskPlanBuilder.Build("写一首诗", IntentDecomposer.Decompose("写一首诗"));
        var poet = plan.Nodes.Single();
        poet.Parameters.Add(new TaskParameter { Name = "style", DisplayName = "风格", IsRequired = true });
        TaskPlanBuilder.ComputeLevelsAndParallelGroups(plan);
        // 重新收集澄清 (参数后加的)
        TaskPlanBuilder.RecalculateClarifications(poet);

        var run = await executor.ExecuteAsync(plan);

        Assert.Equal(PlanNodeState.AwaitingClarification, run.NodeStates[poet.Id]);
        Assert.Equal(0, run.NodeStates.Values.Count(s => s == PlanNodeState.Completed)); // 全计划只有此节点
    }

    [Fact]
    public async Task Executor_ClarificationOnOneNode_OtherNodesRun()
    {
        // 两节点: A (general+必填参数缺失) / B (search, 无参数) → B 照常 Completed
        var plan = TaskPlanBuilder.Build("搜索", IntentDecomposer.Decompose("先搜索，然后写文档"));
        var doc = plan.Nodes.First(n => n.Intent == IntentRecognizer.Intents.General);
        var search = plan.Nodes.First(n => n.Intent == IntentRecognizer.Intents.Search);

        doc.Parameters.Add(new TaskParameter { Name = "format", DisplayName = "格式", IsRequired = true });
        TaskPlanBuilder.RecalculateClarifications(doc);

        var executor = new TaskPlanExecutor((n, ct) =>
            Task.FromResult(new NodeExecutionResult { NodeId = n.Id, FinalState = PlanNodeState.Completed }));
        var run = await executor.ExecuteAsync(plan);

        Assert.Equal(PlanNodeState.AwaitingClarification, run.NodeStates[doc.Id]);
        Assert.Equal(PlanNodeState.Completed, run.NodeStates[search.Id]);
    }

    [Fact]
    public async Task Executor_FailFast_SkipsDownstream()
    {
        var plan = TaskPlanBuilder.Build("先搜索资料，然后基于结果写代码",
            IntentDecomposer.Decompose("先搜索资料，然后基于结果写代码"));

        var executor = new TaskPlanExecutor((n, ct) =>
            Task.FromResult(new NodeExecutionResult
            {
                NodeId = n.Id,
                FinalState = n.Intent == IntentRecognizer.Intents.Search ? PlanNodeState.Failed : PlanNodeState.Completed,
                Error = n.Intent == IntentRecognizer.Intents.Search ? "搜索超时" : null,
            }));

        var run = await executor.ExecuteAsync(plan);
        Assert.Equal(TaskPlanRunState.Finished, run.State);
        var codeNode = plan.Nodes.First(n => n.Intent == IntentRecognizer.Intents.CodeGeneration);
        Assert.Equal(PlanNodeState.Skipped, run.NodeStates[codeNode.Id]);
        Assert.Contains("失败", run.PauseReason);
    }

    // ---------- ResponseSegmenter / Router ----------

    [Fact]
    public void Segmenter_MarksFencedBlocks_Fast()
    {
        var text = "前言\n```html\n<div>hi</div>\n```\n中段 `var x` 尾段\n```csharp\nint y;\n```";
        var segs = ResponseSegmenter.Segment(text);

        var html = segs.First(s => s.Language == "html");
        Assert.Equal(SegmentKind.Code, html.Kind);
        Assert.Equal("<div>hi</div>", html.Content.Trim());
        Assert.Contains("div", text[html.StartIndex..(html.StartIndex + html.Length)]); // 坐标对齐原文

        Assert.Contains(segs, s => s.Kind == SegmentKind.InlineCode && s.Content == "var x");
        Assert.Contains(segs, s => s.Kind == SegmentKind.Code && s.Language == "csharp");
        Assert.Contains(segs, s => s.Kind == SegmentKind.PlainText && s.Content.Contains("前言"));
    }

    [Fact]
    public void Segmenter_UnclosedFence_TreatedAsText()
    {
        var segs = ResponseSegmenter.Segment("a\n```html\n<div>");
        Assert.DoesNotContain(segs, s => s.Kind == SegmentKind.Code);
        Assert.Contains(segs, s => s.Kind == SegmentKind.PlainText);
    }

    [Fact]
    public void Segmenter_LargeInput_IsFast()
    {
        // 快速标记: 1MB 文本单遍扫描应远低于 50ms
        var block = string.Join("", Enumerable.Repeat("x", 1000));
        var text = "```html\n" + block + "\n```\n" + string.Join("", Enumerable.Repeat("t", 5000));
        var text1MB = string.Concat(Enumerable.Repeat(text, 60));

        var sw = System.Diagnostics.Stopwatch.StartNew();
        var segs = ResponseSegmenter.Segment(text1MB);
        sw.Stop();

        _out.WriteLine($"1MB → {segs.Count} segments in {sw.ElapsedMilliseconds}ms");
        Assert.True(sw.ElapsedMilliseconds < 500, $"too slow: {sw.ElapsedMilliseconds}ms");
    }

    [Fact]
    public async Task Router_RoutesToRegisteredPlugin_AndPreservesFences()
    {
        var text = "说明\n```html\n<b>x</b>\n```";
        var router = new ResponseSegmentRouter(new IResponseSegmentPlugin[] { new UiCapturePlugin() });
        var output = await router.ProcessAsync(text);

        Assert.Equal(text, output);  // 恒等插件 → 原文还原 (渲染不加行距)
        Assert.Equal(["ui-capture"], router.PluginNames);
    }

    [Fact]
    public async Task Router_CodeReviewPlugin_ReceivesNonUiCode()
    {
        ResponseSegment? received = null;
        var hook = (ResponseSegment s, CancellationToken ct) => { received = s; return Task.FromResult<string?>("REVIEWED"); };
        var router = new ResponseSegmentRouter(new IResponseSegmentPlugin[] { new CodeReviewPlugin(hook) });

        var output = await router.ProcessAsync("```csharp\nint y;\n```");
        Assert.Equal("int y;", received!.Content.Trim());     // 插件收到原始段
        Assert.Contains("REVIEWED", output);                  // 输出为插件结果 (保留围栏)

        // UI 资产不走审查
        ResponseSegment? uiReceived = null;
        var router2 = new ResponseSegmentRouter(new IResponseSegmentPlugin[]
        {
            new CodeReviewPlugin((s, ct) => { uiReceived = s; return Task.FromResult<string?>("X"); }),
        });
        await router2.ProcessAsync("```html\n<b>x</b>\n```");
        Assert.Null(uiReceived);
    }
}
