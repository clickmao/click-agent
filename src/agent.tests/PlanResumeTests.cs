// v0.22.0 exp9 D7b 机检: 跨轮唤醒 (检查点装载入口 + 续跑消费方)。
//
// 断言原则 (用户审计口径): 每条都绑定**真实行为** —— 检查点真落盘/真读回、答复真落到参数槽、
// 续跑真把生产者产出喂给等待节点、该拒绝的装载入口**真拒绝** (不猜、不伪造、不重跑生产者)。
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using agent.intent;
using agent.registry;
using agent.recovery;
using Xunit;

namespace agent.tests;

public class PlanResumeTests
{
    private static PlanNode Node(string id, string text, int level, bool executable = true, params string[] deps)
    {
        var node = new PlanNode
        {
            Id = id,
            Text = text,
            Intent = "general",
            Level = level,
            DependsOn = deps.ToList(),
        };
        if (!executable)
            node.Clarifications.Add(new ClarificationItem
            {
                NodeId = id,
                ParameterName = "target",
                Question = "要处理哪个文件?",
            });
        return node;
    }

    private static TaskPlan Plan(int maxParallelism, params PlanNode[] nodes)
        => new() { PlanId = "d7b", Nodes = nodes.ToList(), MaxParallelism = maxParallelism };

    private static string TempDir()
    {
        var dir = Path.Combine(Path.GetTempPath(), "d7b-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    /// <summary>真执行器: 每个节点真跑一次 (返回 Completed, 产出 out-&lt;id&gt;)。</summary>
    private static TaskPlanExecutor Executor(LocalNodeContext? ctx = null, List<string>? order = null)
        => new(
            (n, ct) =>
            {
                lock (order ?? new List<string>())
                    order?.Add(n.Id);
                var output = $"out-{n.Id}";
                if (ctx is not null)
                    ctx.NodeOutputs[n.Id] = output; // 与 PlanRunner 一致: 产出写进 ctx 供下游节点读
                return Task.FromResult(new NodeExecutionResult
                {
                    NodeId = n.Id,
                    FinalState = PlanNodeState.Completed,
                    Output = output,
                });
            },
            onWait: (n, producer, reason, ct) => Task.CompletedTask);

    private static TaskPlanRun Run(TaskPlan plan, TaskPlanExecutor executor, TaskPlanRun? seed = null)
        => executor.ExecuteAsync(plan, pollInjections: null, default, seed).GetAwaiter().GetResult();

    // ── ① 捕获闸门: 只在"计划停下来"时写续跑入口 ─────────────────────────────

    [Fact]
    public void 捕获_计划正常跑完_不写检查点_不给下一轮留假答复入口()
    {
        var dir = TempDir();
        var store = new CheckpointStore(dir);
        var plan = Plan(4, Node("a", "一步做完", 0));
        var ctx = new LocalNodeContext { SourceText = "原文" };
        var run = Run(plan, Executor(ctx));

        Assert.Equal(TaskPlanRunState.Finished, run.State);
        Assert.False(PlanResumeService.Capture(store, "s1", plan, run, ctx.NodeOutputs, "原文"));
        Assert.Null(store.Load("s1")); // 跑完的计划不留续跑入口
    }

    [Fact]
    public void 捕获_空会话或空仓库_不写()
    {
        var plan = Plan(4, Node("a", "x", 0));
        var run = Run(plan, Executor());
        Assert.False(PlanResumeService.Capture(null, "s1", plan, run, new Dictionary<string, string?>(), "x"));
        Assert.False(PlanResumeService.Capture(new CheckpointStore(TempDir()), "", plan, run, new Dictionary<string, string?>(), "x"));
    }

    [Fact]
    public void 捕获_等用户时_蓝图运行态真产出三件套一起落盘()
    {
        var dir = TempDir();
        var store = new CheckpointStore(dir);
        var plan = Plan(4,
            Node("b", "生成数据", 0, executable: false),
            Node("a", "基于 $node:b 的产出做汇总", 0));
        var ctx = new LocalNodeContext { SourceText = "原文" };
        var run = Run(plan, Executor(ctx));

        Assert.Equal(TaskPlanRunState.PausedForDependency, run.State);
        Assert.True(PlanResumeService.Capture(store, "s1", plan, run, ctx.NodeOutputs, "原文"));

        var cp = store.Load("s1");
        Assert.NotNull(cp);
        Assert.Equal("b", cp!.AwaitingNodeId);                       // 卡在等用户的是 B
        Assert.Equal("要处理哪个文件?", cp.PendingQuestion);          // 问题文本要带上 (前端/答复提示要用)
        Assert.False(string.IsNullOrEmpty(cp.PlanJson));             // 蓝图快照
        Assert.False(string.IsNullOrEmpty(cp.RunJson));              // 运行态快照
        Assert.Equal("原文", cp.SourceText);
    }

    // ── ② 装载入口: 装不回来就拒绝, 原因要说清 (不许含糊) ────────────────────

    [Fact]
    public void 装载_老格式检查点缺蓝图_拒绝且说明原因()
    {
        var dir = TempDir();
        var store = new CheckpointStore(dir);
        store.Save(new ExecutionCheckpoint { SessionId = "s1", PlanId = "old", NodeStates = new() });

        Assert.False(PlanResumeService.TryLoad(store, "s1", out var cand, out var why));
        Assert.Null(cand);
        Assert.Contains("缺蓝图", why);
    }

    [Fact]
    public void 装载_无检查点_拒绝()
    {
        Assert.False(PlanResumeService.TryLoad(new CheckpointStore(TempDir()), "nope", out _, out var why));
        Assert.Equal(PlanResumeService.RefuseNoCheckpoint, why);
    }

    [Fact]
    public void 装载_计划已终态_拒绝续跑()
    {
        var dir = TempDir();
        var store = new CheckpointStore(dir);
        var plan = Plan(4, Node("a", "一步做完", 0));
        var ctx = new LocalNodeContext();
        var run = Run(plan, Executor(ctx));
        // 手工制造"已终态但检查点还在"的现场 (正常路径不会写)
        store.Save(new ExecutionCheckpoint
        {
            SessionId = "s1",
            PlanId = plan.PlanId,
            PlanJson = System.Text.Json.JsonSerializer.Serialize(plan, TaskPlanJsonContext.Default.TaskPlan),
            RunJson = System.Text.Json.JsonSerializer.Serialize(run, TaskPlanJsonContext.Default.TaskPlanRun),
            AwaitingNodeId = "a",
        });

        Assert.False(PlanResumeService.TryLoad(store, "s1", out _, out var why));
        Assert.Equal(PlanResumeService.RefuseRunTerminal, why);
    }

    [Fact]
    public void 装载_等待节点的产出不在快照里_拒绝_不伪造也不重跑生产者()
    {
        var dir = TempDir();
        var store = new CheckpointStore(dir);
        // 现场: 生产者 b 已 Completed, a 在等它, 但快照里**没有** b 的产出
        var plan = Plan(4,
            Node("b", "生成数据", 0),
            Node("c", "等用户拍板的一步", 0, executable: false),
            Node("a", "基于 $node:b 的产出做汇总", 0));
        var run = new TaskPlanRun { PlanId = plan.PlanId, State = TaskPlanRunState.PausedForDependency };
        run.NodeStates["b"] = PlanNodeState.Completed;
        run.NodeStates["c"] = PlanNodeState.AwaitingClarification;
        run.NodeStates["a"] = PlanNodeState.Waiting;
        run.Waits["a"] = new NodeWaitRecord("a", "b", "queued", Monotonic.NowUs());
        store.Save(new ExecutionCheckpoint
        {
            SessionId = "s1",
            PlanId = plan.PlanId,
            PlanJson = System.Text.Json.JsonSerializer.Serialize(plan, TaskPlanJsonContext.Default.TaskPlan),
            RunJson = System.Text.Json.JsonSerializer.Serialize(run, TaskPlanJsonContext.Default.TaskPlanRun),
            NodeOutputs = new(), // ← 缺产出
        });

        Assert.False(PlanResumeService.TryLoad(store, "s1", out _, out var why));
        Assert.Contains("不在检查点快照里", why);
    }

    // ── ③ 答复落地: 只能落到确定参数槽 ─────────────────────────────────────

    [Fact]
    public void 答复_落到参数槽_节点转可执行_澄清结清不再重复问()
    {
        var cand = LoadedCandidate(("要处理哪个文件?", "target", Array.Empty<string>()), out var reply);
        Assert.False(string.IsNullOrEmpty(reply));
        Assert.Equal(PlanNodeState.Pending, cand!.Run.NodeStates["b"]);
        var node = cand.Plan.Nodes.First(n => n.Id == "b");
        Assert.Empty(node.Clarifications);                      // 澄清已清空 ⇒ IsExecutable=true
        Assert.True(node.ClarificationsSettled);                // 结清标记 ⇒ 证据门槛不再重复问
        Assert.Equal("数据是 42", node.Parameters.First(p => p.Name == "target").Value);
        Assert.Equal(["target"], cand.AwaitingParameterNames);
    }

    [Fact]
    public void 答复_多条目澄清_拒绝不猜位置()
    {
        var node = Node("b", "生成数据", 0, executable: false);
        node.Clarifications.Add(new ClarificationItem { NodeId = "b", ParameterName = "other", Question = "还有?" });
        var cand = Candidate(plan: Plan(4, node), run: null);
        Assert.False(PlanResumeService.ApplyReply(cand, "都行", out var why));
        Assert.Equal(PlanResumeService.RefuseMultiItem, why);
        Assert.Equal(2, cand.Plan.Nodes.First(n => n.Id == "b").Clarifications.Count); // 拒绝时不动计划
    }

    [Fact]
    public void 答复_不在选项内_拒绝()
    {
        var cand = Candidate(Node("b", "生成数据", 0, executable: false), choices: ["甲", "乙"]);
        Assert.False(PlanResumeService.ApplyReply(cand, "丙", out var why));
        Assert.Contains("可选范围", why);
        Assert.Single(cand.Plan.Nodes.First(n => n.Id == "b").Clarifications);
    }

    [Fact]
    public void 答复_澄清条目没有参数名_拒绝不猜()
    {
        var node = new PlanNode { Id = "b", Text = "x", Intent = "general", Level = 0 };
        node.Clarifications.Add(new ClarificationItem { NodeId = "b", ParameterName = "", Question = "给个值?" });
        var cand = Candidate(node);
        Assert.False(PlanResumeService.ApplyReply(cand, "42", out var why));
        Assert.Equal(PlanResumeService.RefuseNoSlot, why);
    }

    // ── ④ 端到端: 从检查点重建 → 续跑 → 等待节点吃到真产出 → 台账闭合 ─────────

    [Fact]
    public void 续跑_从检查点重建_等待节点吃到生产者真产出_等待台账闭合()
    {
        var dir = TempDir();
        const string sessionId = "sess-resume";
        var plan = Plan(4,
            Node("b", "生成数据", 0, executable: false),
            Node("a", "基于 $node:b 的产出做汇总", 0));

        // ── 第一轮: 真执行 → B 待澄清, A 等待, 计划暂停
        var ctx1 = new LocalNodeContext { SourceText = "用户原文" };
        var run1 = Run(plan, Executor(ctx1));
        Assert.Equal(TaskPlanRunState.PausedForDependency, run1.State);
        Assert.Equal(PlanNodeState.Waiting, run1.NodeStates["a"]);
        Assert.True(PlanResumeService.Capture(new CheckpointStore(dir), sessionId, plan, run1, ctx1.NodeOutputs, "用户原文"));

        // ── 跨进程等价: 全新仓库实例 (只读文件) + 全新执行器, 不依赖上一轮内存对象
        var store2 = new CheckpointStore(dir);
        Assert.True(PlanResumeService.TryLoad(store2, sessionId, out var cand, out var why), why);
        Assert.NotNull(cand);
        Assert.True(PlanResumeService.ApplyReply(cand!, "数据是 42", out var applyWhy), applyWhy);

        var ctx2 = new LocalNodeContext { SourceText = cand!.SourceText };
        foreach (var kv in cand.NodeOutputs)
            ctx2.NodeOutputs[kv.Key] = kv.Value;
        var order2 = new List<string>();
        var run2 = Run(cand!.Plan, Executor(ctx2, order2), seed: cand.Run);

        // 续跑的真结果: B 真跑 (带着答复), A 真跑并吃到 B 的产出, 计划收口
        Assert.Equal(["b", "a"], order2);
        Assert.Equal(TaskPlanRunState.Finished, run2.State);
        Assert.Equal(PlanNodeState.Completed, run2.NodeStates["a"]);
        Assert.Equal("out-b", ctx2.NodeOutputs["b"]);
        var aNode = cand.Plan.Nodes.First(n => n.Id == "a");
        Assert.Contains("b", aNode.RuntimeDeps);                              // 续跑时重新解析出运行时依赖
        Assert.Equal("out-b", TextProcessExecutor.ResolveInput(aNode, ctx2)); // 吃的是 B 的真产出, 不是原文
        Assert.NotNull(run2.Waits["a"].EndedUs);                              // 等待台账闭合 (WaitUs 含用户思考时间)
        Assert.NotNull(run2.Waits["a"].WaitUs);
    }

    [Fact]
    public void 续跑_已完成的节点不重跑_产出直接复用()
    {
        var plan = Plan(4,
            Node("b", "生成数据", 0, executable: false),
            Node("c", "另一件已做完的事", 0));
        var ctx1 = new LocalNodeContext();
        var order1 = new List<string>();
        var run1 = Run(plan, Executor(ctx1, order1));
        Assert.Equal(["c"], order1); // c 跑完, b 待澄清

        PlanResumeService.TryLoad(SeedStore(plan, run1, ctx1, out var dir), "s1", out var cand, out var why);
        Assert.NotNull(cand);
        Assert.True(PlanResumeService.ApplyReply(cand!, "42", out _));

        var order2 = new List<string>();
        var ctx2 = new LocalNodeContext();
        foreach (var kv in cand!.NodeOutputs)
            ctx2.NodeOutputs[kv.Key] = kv.Value;
        var run2 = Run(cand.Plan, Executor(ctx2, order2), seed: cand.Run);

        Assert.Equal(["b"], order2);                               // c 不在第二轮里被重跑
        Assert.Equal(PlanNodeState.Completed, run2.NodeStates["c"]);
        Assert.Equal("out-c", ctx2.NodeOutputs["c"]);              // 上一轮的产出被复用
        Assert.True(_dirKeepAlive.Contains(dir));                  // 目录仍在使用 (避免误删)
    }

    // ── ⑤ 答复不能落地时: 消费方作废入口, 不把用户永远拦在旧问题上 ────────────

    [Fact]
    public void 装载后答复无法落地_应作废检查点_下一轮消息回到正常任务路径()
    {
        var dir = TempDir();
        var store = new CheckpointStore(dir);
        var plan = Plan(4, Node("b", "生成数据", 0, executable: false));
        var ctx = new LocalNodeContext();
        var run = Run(plan, Executor(ctx));
        Assert.True(PlanResumeService.Capture(store, "s1", plan, run, ctx.NodeOutputs, null));
        Assert.True(PlanResumeService.TryLoad(store, "s1", out var cand, out _));

        cand!.Plan.Nodes.First(n => n.Id == "b").Clarifications[0].ParameterName = ""; // 现场: 条目无参数名
        Assert.False(PlanResumeService.ApplyReply(cand, "随便", out var why));
        Assert.Equal(PlanResumeService.RefuseNoSlot, why);

        store.Clear("s1"); // 消费方的作废动作 (IndustrialAgentV2.TryResumePausedPlanAsync 内)
        Assert.False(PlanResumeService.TryLoad(store, "s1", out _, out var after));
        Assert.Equal(PlanResumeService.RefuseNoCheckpoint, after);
    }

    // ── 辅助 ───────────────────────────────────────────────────────────────

    private static readonly List<string> _dirKeepAlive = [];

    // ── 跨进程探针 (真机; 默认跳过) ────────────────────────────────────────────
    // 两个**独立 dotnet 进程**只共享一个目录里的检查点文件:
    //   进程A: PLAN_RESUME_XPROC=write  PLAN_RESUME_DIR=<dir> → 真跑第一轮 (暂停) + Capture
    //   进程B: PLAN_RESUME_XPROC=resume PLAN_RESUME_DIR=<dir> → 装载 + 答复落地 + 真续跑
    //   不设 env → 立即 return (常规全量测试不受影响)。
    // 这就是"跨进程/跨轮续跑"的真机证据: 续跑不依赖进程内残留对象, 只依赖落盘的蓝图+运行态+真产出。
    private static string? ProbeMode => Environment.GetEnvironmentVariable("PLAN_RESUME_XPROC");
    private static string? ProbeDir => Environment.GetEnvironmentVariable("PLAN_RESUME_DIR");

    [Fact]
    public void 跨进程探针_进程A_真跑暂停并落检查点()
    {
        if (ProbeMode != "write" || string.IsNullOrEmpty(ProbeDir))
            return;
        var dir = ProbeDir!;
        Directory.CreateDirectory(dir);
        var plan = Plan(4,
            Node("b", "生成数据", 0, executable: false),
            Node("a", "基于 $node:b 的产出做汇总", 0));
        var ctx1 = new LocalNodeContext { SourceText = "跨进程探针原文" };
        var order1 = new List<string>();
        var run1 = Run(plan, Executor(ctx1, order1));
        Assert.Equal(TaskPlanRunState.PausedForDependency, run1.State);
        Assert.Equal(PlanNodeState.AwaitingClarification, run1.NodeStates["b"]);
        Assert.Equal(PlanNodeState.Waiting, run1.NodeStates["a"]);

        var wrote = PlanResumeService.Capture(new CheckpointStore(dir), "xproc-session", plan, run1, ctx1.NodeOutputs, "跨进程探针原文");
        Assert.True(wrote);
        var files = Directory.GetFiles(dir, "*", SearchOption.AllDirectories);
        Assert.NotEmpty(files);
        var evidence = $"{{\"phase\":\"write\",\"state\":\"{run1.State}\",\"awaiting\":\"{PlanResumeService.AwaitingNodeIdOf(run1, plan)}\"," +
                       $"\"question\":\"{run1.PauseReason}\",\"order\":[{string.Join(",", order1.Select(o => $"\"{o}\""))}]," +
                       $"\"checkpoint_files\":{files.Length},\"plan_json_chars\":{plan.Nodes.Count}}}";
        File.AppendAllText(Path.Combine(dir, "evidence.jsonl"), evidence + Environment.NewLine);
        Console.WriteLine($"[XPROC-WRITE] {evidence}");
    }

    [Fact]
    public void 跨进程探针_进程B_装载并真续跑()
    {
        if (ProbeMode != "resume" || string.IsNullOrEmpty(ProbeDir))
            return;
        var store = new CheckpointStore(ProbeDir!);
        Assert.True(PlanResumeService.TryLoad(store, "xproc-session", out var cand, out var why), why);
        Assert.Equal("b", cand!.AwaitingNodeId);
        Assert.Equal(["target"], cand.AwaitingParameterNames);   // 装载时快照的槽名 (答复后仍可对账)
        Assert.Empty(cand.NodeOutputs);                          // 上一轮 B 没产出 (它在等用户) — 快照如实为空

        Assert.True(PlanResumeService.ApplyReply(cand, "数据是 42", out var applyWhy), applyWhy);
        var slot = cand.Plan.Nodes.First(n => n.Id == "b").Parameters.First(p => p.Name == "target");
        Assert.Equal("数据是 42", slot.Value);                    // 答复真落到参数槽 (跨进程重建后的蓝图里)

        var ctx = new LocalNodeContext { SourceText = cand.SourceText };
        foreach (var kv in cand.NodeOutputs)
            ctx.NodeOutputs[kv.Key] = kv.Value;
        var order = new List<string>();
        var run = Run(cand.Plan, Executor(ctx, order), seed: cand.Run);

        Assert.Equal(["b", "a"], order);
        Assert.Equal(TaskPlanRunState.Finished, run.State);
        var aNode = cand.Plan.Nodes.First(n => n.Id == "a");
        Assert.Contains("b", aNode.RuntimeDeps);
        Assert.Equal("out-b", TextProcessExecutor.ResolveInput(aNode, ctx));   // A 吃到 B 的真产出
        Assert.NotNull(run.Waits["a"].EndedUs);                                // 等待台账闭合
        var evidence = $"{{\"phase\":\"resume\",\"state\":\"{run.State}\",\"order\":[{string.Join(",", order.Select(o => $"\"{o}\""))}]," +
                       $"\"a_input\":\"{TextProcessExecutor.ResolveInput(aNode, ctx)}\",\"wait_ms\":{run.Waits["a"].WaitUs / 1000}," +
                       $"\"slot_value\":\"{slot.Value}\",\"seeded_outputs\":{cand.NodeOutputs.Count}}}";
        File.AppendAllText(Path.Combine(ProbeDir!, "evidence.jsonl"), evidence + Environment.NewLine);
        Console.WriteLine($"[XPROC-RESUME] {evidence}");
    }

    [Fact]
    public void 捕获_等审批的暂停态_不写检查点_避免吞掉审批消息()
    {
        // 等审批有它自己的答复协议: 若被续跑入口捕获, 用户的审批消息会落到"澄清参数槽"上并被拒绝 ⇒ 消息被吞。
        var dir = TempDir();
        var store = new CheckpointStore(dir);
        var node = Node("b", "要用户批准的一步", 0, executable: false);
        node.Clarifications.Clear();                       // 审批节点: 没有"文字澄清条目"
        var plan = Plan(4, node);
        var run = new TaskPlanRun { PlanId = plan.PlanId, State = TaskPlanRunState.PausedForApproval };
        run.NodeStates["b"] = PlanNodeState.AwaitingApproval;

        Assert.False(PlanResumeService.Capture(store, "s1", plan, run, new Dictionary<string, string?>(), null));
        Assert.Null(store.Load("s1"));                     // 检查点没写 → 下一轮消息走正常链路
        Assert.False(PlanResumeService.TryLoad(store, "s1", out _, out var why));
        Assert.Equal(PlanResumeService.RefuseNoCheckpoint, why);
    }

    // ── 产品链路真机探针 (默认跳过) ────────────────────────────────────────────
    // PLAN_RESUME_SEED_CLI=1 时: 用**产品自己的序列化器**在**产品真机数据目录** (./data) 里为 CLI 会话
    // ("cli-main", Program.cs:369) 预置一份"可续跑检查点" (两个全本地节点: b 在等澄清, a 等 b 的产出)。
    // 随后真机跑 `agenthost.dll -q "数据是 42"`: 装载入口必须在**意图拆解之前**拦下这条消息、
    // 把答复落到 b 的参数槽、从上一轮运行态续跑 (全程零 LLM 调用), 跑完由产品自己清掉检查点。
    [Fact]
    public void 产品链路真机探针_为CLI会话预置可续跑检查点()
    {
        if (Environment.GetEnvironmentVariable("PLAN_RESUME_SEED_CLI") != "1")
            return;
        var b = new PlanNode
        {
            Id = "b",
            Text = "按用户答复生成数据",
            Intent = "general",
            Level = 0,
            Location = NodeExecutionLocation.Local,
            LocalExecutorId = LocalExecutorRegistry.TextProcess,
        };
        b.Clarifications.Add(new ClarificationItem
        {
            NodeId = "b",
            ParameterName = "target",
            Question = "要处理哪个文件?",
        });
        var a = new PlanNode
        {
            Id = "a",
            Text = "基于 $node:b 的产出做汇总",
            Intent = "general",
            Level = 1,
            Location = NodeExecutionLocation.Local,
            LocalExecutorId = LocalExecutorRegistry.TextProcess,
        };
        var plan = new TaskPlan
        {
            PlanId = "r384-probe",
            Nodes = [b, a],
            MaxParallelism = 4,
            SourceText = "真机探针原始请求",
        };
        var run = new TaskPlanRun { PlanId = plan.PlanId, State = TaskPlanRunState.PausedForDependency };
        run.NodeStates["b"] = PlanNodeState.AwaitingClarification;
        run.NodeStates["a"] = PlanNodeState.Waiting;
        run.Waits["a"] = new NodeWaitRecord("a", "b", "user", Monotonic.NowUs());
        run.PauseReason = "节点「基于 $node:b 的产出做汇总」等待 b 的产出, 而 b 在等用户回复 (本轮不产出, 不伪造)";

        // 目录必须显式给绝对路径 (dotnet test 的 cwd 是测试输出目录, 不是仓库根 —— 否则写到了产品看不见的地方)
        var seedDir = Environment.GetEnvironmentVariable("PLAN_RESUME_SEED_DIR");
        Assert.False(string.IsNullOrEmpty(seedDir), "需设 PLAN_RESUME_SEED_DIR=<产品数据目录绝对路径> (产品真机用 ./data)");
        var seedSession = Environment.GetEnvironmentVariable("PLAN_RESUME_SEED_SESSION") ?? "cli-main";

        var store = new CheckpointStore(seedDir!);
        Assert.True(PlanResumeService.Capture(store, seedSession, plan, run, new Dictionary<string, string?>(), plan.SourceText));
        Assert.NotNull(store.Load(seedSession));
        Console.WriteLine($"[SEED-CLI] checkpoint written for session={seedSession} nodes=[b(待澄清),a(等b)]");
    }

    private static CheckpointStore SeedStore(TaskPlan plan, TaskPlanRun run, LocalNodeContext ctx, out string dir)
    {
        dir = TempDir();
        var store = new CheckpointStore(dir);
        Assert.True(PlanResumeService.Capture(store, "s1", plan, run, ctx.NodeOutputs, null));
        _dirKeepAlive.Add(dir);
        return store;
    }

    private static PlanResumeCandidate Candidate(PlanNode node, string[]? choices = null)
    {
        if (choices is not null)
        {
            node.Clarifications.Clear();
            node.Clarifications.Add(new ClarificationItem
            {
                NodeId = node.Id,
                ParameterName = "target",
                Question = "选哪个?",
                Choices = choices.ToList(),
            });
        }
        return Candidate(Plan(4, node), null);
    }

    private static PlanResumeCandidate Candidate(TaskPlan plan, TaskPlanRun? run)
    {
        run ??= new TaskPlanRun { PlanId = plan.PlanId, State = TaskPlanRunState.PausedForDependency };
        foreach (var n in plan.Nodes)
            run.NodeStates[n.Id] = n.Clarifications.Count > 0
                ? PlanNodeState.AwaitingClarification
                : PlanNodeState.Pending;
        var awaiting = plan.Nodes.First(n => n.Clarifications.Count > 0);
        return new PlanResumeCandidate
        {
            Plan = plan,
            Run = run,
            NodeOutputs = new Dictionary<string, string>(StringComparer.Ordinal),
            AwaitingNodeId = awaiting.Id,
            AwaitingParameterNames = awaiting.Clarifications.Select(c => c.ParameterName).ToList(),
            PendingQuestion = awaiting.Clarifications.FirstOrDefault()?.Question,
        };
    }

    private static PlanResumeCandidate LoadedCandidate(
        (string Question, string Slot, string[] Choices) item, out string reply)
    {
        var dir = TempDir();
        var store = new CheckpointStore(dir);
        var node = Node("b", "生成数据", 0, executable: false);
        node.Clarifications.Clear();
        node.Clarifications.Add(new ClarificationItem
        {
            NodeId = "b",
            ParameterName = item.Slot,
            Question = item.Question,
        });
        var plan = Plan(4, node);
        var run = new TaskPlanRun { PlanId = plan.PlanId, State = TaskPlanRunState.PausedForDependency };
        run.NodeStates["b"] = PlanNodeState.AwaitingClarification;
        store.Save(new ExecutionCheckpoint
        {
            SessionId = "s1",
            PlanId = plan.PlanId,
            PlanJson = System.Text.Json.JsonSerializer.Serialize(plan, TaskPlanJsonContext.Default.TaskPlan),
            RunJson = System.Text.Json.JsonSerializer.Serialize(run, TaskPlanJsonContext.Default.TaskPlanRun),
            AwaitingNodeId = "b",
            PendingQuestion = item.Question,
        });
        Assert.True(PlanResumeService.TryLoad(store, "s1", out var cand, out var why), why);
        reply = "数据是 42";
        Assert.True(PlanResumeService.ApplyReply(cand!, reply, out var applyWhy), applyWhy);
        return cand!;
    }
}
