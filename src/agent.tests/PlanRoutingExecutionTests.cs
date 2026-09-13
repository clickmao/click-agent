using agent.intent;
using agent.registry;
using Xunit;
using Xunit.Abstractions;

namespace agent.tests;

/// <summary>
/// v0.22.0 exp9 D1-D3 机检:
///   D1 数据模型  — 计划节点带执行位置 (本地/远程/Hybrid) 且进 JSON 契约 (AOT source-gen 面)。
///   D2 确定性判定 — 路由只由登记表 + 规则决定 (未接线/未登记 ⇒ 必须 Remote, 负向控制)。
///   D3 真执行体  — 本地节点真被执行器跑 (哑体只允许在闸门关闭时出现; 源码级反向断言哑体已拆除)。
/// </summary>
public class PlanRoutingExecutionTests
{
    private readonly ITestOutputHelper _out;

    public PlanRoutingExecutionTests(ITestOutputHelper output) => _out = output;

    private static readonly string RepoRoot = FindRepoRoot();

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    private static IntentDecomposer.SubTask St(
        string text, string intent, IntentDecomposer.TaskRelation rel = IntentDecomposer.TaskRelation.None) =>
        new(text, intent, false, 0, rel);

    private static TaskPlan Routed(params IntentDecomposer.SubTask[] subs) =>
        RoutedPlanBuilder.Build("测试源文本", subs);

    private static PlanNode Node(string text, string intent) => new() { Id = "n_t", Text = text, Intent = intent };

    /// <summary>本地执行器探针: 记录被调次数 (哑体不会调用它 → 反向断言的核心证据)</summary>
    private sealed class CountingExecutor : ILocalNodeExecutor
    {
        public int Calls;

        public string Id => LocalExecutorRegistry.PythonSelfTest;

        public Task<NodeExecutionResult> RunAsync(PlanNode node, LocalNodeContext ctx, CancellationToken ct)
        {
            Interlocked.Increment(ref Calls);
            return Task.FromResult(new NodeExecutionResult
            {
                NodeId = node.Id, FinalState = PlanNodeState.Completed, Output = "counted",
            });
        }
    }

    // ── D1 ─────────────────────────────────────────────────────────────────────

    [Fact]
    public void D1_Routed_Plan_Carries_Location_Executor_And_Hint()
    {
        var plan = Routed(St("用 python 写一个贪吃蛇游戏", IntentRecognizer.Intents.CodeGeneration));

        var gen = plan.Nodes.First(n => n.Intent == IntentRecognizer.Intents.CodeGeneration);
        Assert.Equal(NodeExecutionLocation.Remote, gen.Location);
        Assert.Equal("remote", gen.LocationText);
        Assert.False(gen.RunsLocally);

        var verify = plan.Nodes.First(n => n.LocalExecutorId == LocalExecutorRegistry.PythonSelfTest);
        Assert.Equal(NodeExecutionLocation.Local, verify.Location);
        Assert.Equal("local", verify.LocationText);
        Assert.True(verify.RunsLocally, "本地节点必须 RunsLocally=true (调度器据此并发先行)");
        Assert.False(string.IsNullOrWhiteSpace(verify.LocalHint), "本地判定必须带依据短句 (前端可见)");
        Assert.Contains(verify.Id, plan.LocalExecutableNodeIds);
        Assert.Contains(gen.Id, verify.DependsOn);   // 依赖驱动: 产物就绪才跑

        // 本地节点留在本地, 远程节点不进本地集合
        Assert.DoesNotContain(gen.Id, plan.LocalExecutableNodeIds);
    }

    [Fact]
    public void D1_Location_Is_In_Json_Contract()
    {
        var plan = Routed(St("用 python 写一个贪吃蛇游戏", IntentRecognizer.Intents.CodeGeneration));
        var json = TaskPlanJsonContext.ToJson(plan);

        Assert.Contains("\"LocationText\": \"local\"", json);
        Assert.Contains("\"LocalExecutorId\": \"python.selftest\"", json);
        Assert.Contains("\"LocalHint\":", json);

        // 执行审计面 (前端 D5 / KPI D6 读的就是它) 必须也能走 source-gen 序列化
        var run = new TaskPlanRun
        {
            RunId = "r1",
            PlanId = plan.PlanId,
            Outcomes =
            [
                new NodeOutcome
                {
                    NodeId = "n1", Location = "local", ExecutorId = LocalExecutorRegistry.PythonSelfTest,
                    State = PlanNodeState.Completed, Tokens = 0, ElapsedMs = 12, Detail = "selftest exit=0",
                },
            ],
        };
        var runJson = TaskPlanJsonContext.ToJson(run);
        Assert.Contains("\"Outcomes\":", runJson);
        Assert.Contains("\"Location\": \"local\"", runJson);
        Assert.Contains("\"ExecutorId\": \"python.selftest\"", runJson);
    }

    // ── D2 ─────────────────────────────────────────────────────────────────────

    [Fact]
    public void D2_Negative_Control_Unwired_Or_Unknown_Intent_Is_Never_Local()
    {
        // 登记表里存在但**未接线**的能力: 不许路由到它 (负向控制)
        Assert.False(LocalExecutorRegistry.IsWired(LocalExecutorRegistry.RealMachineReplay));
        Assert.False(LocalExecutorRegistry.IsWired(LocalExecutorRegistry.LocalCommand));

        var cases = new[]
        {
            IntentRecognizer.Intents.FileOperation,   // 已登记(未接线) 且参数未齐
            IntentRecognizer.Intents.GitOperation,    // 已登记(未接线)
            IntentRecognizer.Intents.General,         // 未登记
            IntentRecognizer.Intents.Search,          // 未登记
            "完全没见过的意图",
        };

        foreach (var intent in cases)
        {
            var d = PlanRoutePolicy.Decide(Node("随便", intent));
            Assert.Equal(NodeExecutionLocation.Remote, d.Location);
            Assert.Null(d.ExecutorId);
            Assert.False(string.IsNullOrWhiteSpace(d.Hint));
        }
    }

    [Fact]
    public void D2_Wired_Local_Intent_Is_Local()
    {
        var d = PlanRoutePolicy.Decide(Node("本地跑产物自测", PlanNodeIntents.VerifyLocal));
        Assert.Equal(NodeExecutionLocation.Local, d.Location);
        Assert.Equal(LocalExecutorRegistry.PythonSelfTest, d.ExecutorId);
        Assert.True(LocalExecutorRegistry.IsWired(d.ExecutorId));
    }

    [Fact]
    public void D2_Generation_Is_Remote_Unless_Text_Also_Contains_A_Wired_Local_Action()
    {
        // 纯生成 → 远程
        var remote = PlanRoutePolicy.Decide(Node("写一个贪吃蛇游戏", IntentRecognizer.Intents.CodeGeneration));
        Assert.Equal(NodeExecutionLocation.Remote, remote.Location);
        Assert.Null(remote.ExecutorId);

        // 生成 + 本地可做的一段 (统计) → Hybrid (远程生成后本地立刻跑, 不新增 LLM 调用)
        var hybrid = PlanRoutePolicy.Decide(Node("写一个 python 脚本并统计代码行数", IntentRecognizer.Intents.CodeGeneration));
        Assert.Equal(NodeExecutionLocation.Hybrid, hybrid.Location);
        Assert.Equal(LocalExecutorRegistry.TextProcess, hybrid.ExecutorId);

        // 生成 + 需要**未接线**动作 → 不升级 Hybrid (负向控制)
        var unwired = PlanRoutePolicy.Decide(Node("写一个贪吃蛇游戏并真机按键回放", IntentRecognizer.Intents.CodeGeneration));
        Assert.Equal(NodeExecutionLocation.Remote, unwired.Location);
    }

    [Fact]
    public void D2_SelfTest_Post_Action_Splits_Into_Remote_Plus_Local_Nodes()
    {
        // 本节点 = 远程生成 (本地自测不藏在 Hybrid 里, 单列一个 Local 节点 — 前端才看得清"哪步本地")
        var d = PlanRoutePolicy.Decide(Node("用 python 写一个贪吃蛇，自测通过后交付", IntentRecognizer.Intents.CodeGeneration));
        Assert.Equal(NodeExecutionLocation.Remote, d.Location);
        Assert.Null(d.ExecutorId);

        var plan = Routed(St("用 python 写一个贪吃蛇，自测通过后交付", IntentRecognizer.Intents.CodeGeneration));
        Assert.Equal(2, plan.Nodes.Count);
        var gen = plan.Nodes.Single(n => n.Intent == IntentRecognizer.Intents.CodeGeneration);
        var verify = plan.Nodes.Single(n => n.Intent == PlanNodeIntents.VerifyLocal);
        Assert.Equal(NodeExecutionLocation.Remote, gen.Location);
        Assert.Equal(NodeExecutionLocation.Local, verify.Location);
        Assert.Equal(1, verify.Level);              // 层级 = 依赖生成节点
        Assert.Equal(gen.Id, verify.DependsOn.Single());
    }

    [Fact]
    public void D2_Verify_Node_Append_Is_Idempotent()
    {
        var subs = new[] { St("写一个贪吃蛇游戏", IntentRecognizer.Intents.CodeGeneration) };
        var plan = RoutedPlanBuilder.Build("src", subs);
        var count = plan.Nodes.Count;
        Assert.True(count >= 2, "生成节点 + 至少一个本地验证节点");

        LocalVerifyNodePlanner.AppendFor(plan);
        Assert.Equal(count, plan.Nodes.Count);   // 重复追加 = 0 新增

        var again = RoutedPlanBuilder.Build("src", subs);
        Assert.Equal(count, again.Nodes.Count);
    }

    // ── D3 ─────────────────────────────────────────────────────────────────────

    [Fact]
    public async Task D3_Real_Runner_Executes_Local_Nodes__Dummy_Only_When_Gate_Off()
    {
        var probe = new CountingExecutor();
        var plan = Routed(St("写一个贪吃蛇游戏", IntentRecognizer.Intents.CodeGeneration));
        var verifyId = plan.Nodes.First(n => n.LocalExecutorId == LocalExecutorRegistry.PythonSelfTest).Id;

        // 闸门开 (缺省) → 真执行体: 本地节点真被跑
        var runner = new PlanRunner([probe, new TextProcessExecutor()], ledger: null, gate: () => true);
        var ctx = new LocalNodeContext { RemoteText = "print('artifact')", ArtifactPath = null };
        var run = await runner.RunAsync(plan, ctx);

        Assert.Equal(PlanNodeState.Completed, run.NodeStates[verifyId]);
        Assert.Equal(1, probe.Calls);
        Assert.Contains(run.Outcomes, o => o.NodeId == verifyId && o.Location == "local" && o.Tokens == 0);
        Assert.DoesNotContain(run.Outcomes, o => o.NodeId == verifyId && o.State == PlanNodeState.Skipped);

        // 闸门关 → 唯一允许的哑体路径: 全部 Skipped 且**不**调用执行器
        var off = new PlanRunner([probe, new TextProcessExecutor()], ledger: null, gate: () => false);
        var run2 = await off.RunAsync(plan, ctx);
        Assert.NotEmpty(run2.Outcomes);
        Assert.All(run2.Outcomes, o => Assert.Equal(PlanNodeState.Skipped, o.State));
        Assert.Equal(1, probe.Calls);
    }

    [Fact]
    public async Task D3_Hybrid_Node_Runs_Locally_On_Remote_Text_Without_New_Llm_Call()
    {
        var plan = Routed(St("写一个 python 脚本并统计代码行数", IntentRecognizer.Intents.CodeGeneration));
        var hybrid = plan.Nodes.Single(n => n.Location == NodeExecutionLocation.Hybrid);

        var runner = new PlanRunner([new PythonSelfTestExecutor(), new TextProcessExecutor()], ledger: null, gate: () => true);
        var run = await runner.RunAsync(plan, new LocalNodeContext { RemoteText = "line1\nline2\n" });

        Assert.Equal(PlanNodeState.Completed, run.NodeStates[hybrid.Id]);
        var outcome = run.Outcomes.Single(o => o.NodeId == hybrid.Id);
        Assert.Equal("hybrid", outcome.Location);
        Assert.Equal(0, outcome.Tokens);
        Assert.Contains("本地统计", outcome.Detail);
    }

    [Fact]
    public async Task D3_PythonSelfTest_Executor_Real_Subprocess_Exit_Code_Is_The_Verdict()
    {
        var dir = Path.Combine(Path.GetTempPath(), "r381_plan_" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(dir);
        try
        {
            var good = Path.Combine(dir, "good.py");
            await File.WriteAllTextAsync(good,
                "import sys\nif __name__ == '__main__':\n    if '--selftest' in sys.argv:\n        print('SELFTEST OK 3/3')\n        sys.exit(0)\n    print('run')\n");
            var bad = Path.Combine(dir, "bad.py");
            await File.WriteAllTextAsync(bad,
                "import sys\nif __name__ == '__main__':\n    if '--selftest' in sys.argv:\n        print('SELFTEST FAIL 1/3')\n        sys.exit(1)\n");
            var nocon = Path.Combine(dir, "nocontract.py");
            await File.WriteAllTextAsync(nocon, "print('no selftest hook here')\n");

            var exec = new PythonSelfTestExecutor();
            var node = new PlanNode
            {
                Id = "v1", Text = "本地跑自测", Intent = PlanNodeIntents.VerifyLocal,
                Location = NodeExecutionLocation.Local, LocalExecutorId = LocalExecutorRegistry.PythonSelfTest,
            };

            // 1) 真跑 exit=0 → Completed
            var ok = await exec.RunAsync(node, new LocalNodeContext { ArtifactPath = good, PythonRunGate = () => true }, default);
            Assert.Equal(PlanNodeState.Completed, ok.FinalState);
            Assert.Contains("exit=0", ok.Output);

            // 2) 真跑 exit=1 → Failed + 真原因 (不静默成功)
            var f1 = await exec.RunAsync(node, new LocalNodeContext { ArtifactPath = bad, PythonRunGate = () => true }, default);
            Assert.Equal(PlanNodeState.Failed, f1.FinalState);
            Assert.Contains("exit=1", f1.Error);

            // 3) 产物缺 --selftest 契约 → Failed (没有判据就说没有, 不假装跑过)
            var f2 = await exec.RunAsync(node, new LocalNodeContext { ArtifactPath = nocon, PythonRunGate = () => true }, default);
            Assert.Equal(PlanNodeState.Failed, f2.FinalState);
            Assert.Contains("--selftest", f2.Error);

            // 4) 无产物 → Failed
            var f3 = await exec.RunAsync(node, new LocalNodeContext { ArtifactPath = null, PythonRunGate = () => true }, default);
            Assert.Equal(PlanNodeState.Failed, f3.FinalState);

            // 5) 运行级闸门关 → Skipped (诚实登记, 不是成功也不是失败)
            var gated = await exec.RunAsync(node, new LocalNodeContext { ArtifactPath = good, PythonRunGate = () => false }, default);
            Assert.Equal(PlanNodeState.Skipped, gated.FinalState);
            Assert.Contains("AGENTFRAMEWORK_PY_RUN", gated.Error);
        }
        finally
        {
            try { Directory.Delete(dir, recursive: true); } catch { /* 清理失败不影响判据 */ }
        }
    }

    [Fact]
    public async Task D3_TextProcess_Executor_Is_Deterministic_And_Refuses_Empty_Input()
    {
        var exec = new TextProcessExecutor();
        var node = new PlanNode
        {
            Id = "t1", Text = "本地统计", Intent = PlanNodeIntents.TextProcessing,
            Location = NodeExecutionLocation.Local, LocalExecutorId = LocalExecutorRegistry.TextProcess,
        };

        var r1 = await exec.RunAsync(node, new LocalNodeContext { RemoteText = "abc\n中文行\n" }, default);
        Assert.Equal(PlanNodeState.Completed, r1.FinalState);
        Assert.Contains("字符=", r1.Output);
        Assert.Contains("指纹=", r1.Output);

        var r2 = await exec.RunAsync(node, new LocalNodeContext { RemoteText = "abc\n中文行\n" }, default);
        Assert.Equal(r1.Output, r2.Output);   // 确定性 (无时间戳漂移)

        var r3 = await exec.RunAsync(node, new LocalNodeContext(), default);
        Assert.Equal(PlanNodeState.Failed, r3.FinalState);
    }

    [Fact]
    public void D3_Reverse_Assertion_Dummy_Runner_Is_Gone_From_Main_Chain()
    {
        var src = File.ReadAllText(Path.Combine(RepoRoot, "src", "agent", "IndustrialAgentV2.cs"));

        Assert.DoesNotContain("影子不产真输出", src);      // 哑体注释已删除
        Assert.DoesNotContain("RunShadowPlanAsync", src);  // 哑体入口已删除
        Assert.Contains("RoutedPlanBuilder.Build(", src);  // 计划构建走带路由的单一入口
        Assert.Contains("RunPlanAsync(", src);             // 真执行体已接线
        Assert.Contains("_lastPlanRun", src);              // 执行结论可查
    }

    [Fact]
    public void Integration_Real_Request_Routes_To_Local_And_Remote_Nodes()
    {
        const string request = "用 python 开发一个贪吃蛇游戏，自测通过后统计代码行数";
        var plan = Routed(IntentDecomposer.Decompose(request).ToArray());

        foreach (var n in plan.Nodes)
            _out.WriteLine($"{n.Id} loc={n.LocationText} exec={n.LocalExecutorId ?? "-"} intent={n.Intent} deps=[{string.Join(",", n.DependsOn)}] {n.Text}");

        // 需要模型产内容的节点 (Remote) 与零 token 本地节点必须都在: 用户要的"哪步远程/哪步本地"可显示
        Assert.Contains(plan.Nodes, n => n.Location == NodeExecutionLocation.Remote);
        Assert.Contains(plan.Nodes, n => n.RunsLocally);
        Assert.All(plan.Nodes.Where(n => n.Location != NodeExecutionLocation.Remote),
            n => Assert.True(LocalExecutorRegistry.IsWired(n.LocalExecutorId)));
    }
}
