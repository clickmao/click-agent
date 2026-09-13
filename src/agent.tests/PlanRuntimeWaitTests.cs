// v0.22.0 exp9 D7 机检: 运行时依赖等待 (A 跑到中途要用 B 的产出, 而 B 未产出/在等用户)。
//
// 断言原则 (用户审计口径): 每条都绑定调度器**真实行为** —— 状态序列、谁先跑、等的是谁、
// 失败是否如实 (不静默兜底)、成环是否被拒、等待是否占额度。
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using agent.intent;
using agent.registry;
using Xunit;

namespace agent.tests;

public class PlanRuntimeWaitTests
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
            }); // Clarifications 非空 ⇒ IsExecutable=false ⇒ 调度器置 AwaitingClarification
        return node;
    }

    private static TaskPlan Plan(int maxParallelism, params PlanNode[] nodes)
        => new() { PlanId = "d7", Nodes = nodes.ToList(), MaxParallelism = maxParallelism };

    /// <summary>记录执行顺序 + 等待事件的执行体 (每个节点名执行一次, 返回 Completed)</summary>
    private static TaskPlanExecutor Executor(List<string> order, List<(string Node, string Producer, string Reason)> waits,
        Func<PlanNode, int, NodeExecutionResult>? custom = null)
    {
        var count = new Dictionary<string, int>(StringComparer.Ordinal);
        return new TaskPlanExecutor(
            (n, ct) =>
            {
                lock (order)
                {
                    order.Add(n.Id);
                    count.TryGetValue(n.Id, out var c);
                    count[n.Id] = c + 1;
                }
                var result = custom?.Invoke(n, count[n.Id]);
                return Task.FromResult(result ?? new NodeExecutionResult
                {
                    NodeId = n.Id,
                    FinalState = PlanNodeState.Completed,
                    Output = $"out-{n.Id}",
                });
            },
            onWait: (n, producer, reason, ct) =>
            {
                lock (waits)
                    waits.Add((n.Id, producer, reason));
                return Task.CompletedTask;
            });
    }

    [Fact]
    public void A中途要B产出_B未产出时A等待_B产出后A继续()
    {
        var order = new List<string>();
        var waits = new List<(string Node, string Producer, string Reason)>();
        // 同层: 先声明 B, 再声明 A(A 通过 $node:b 引用 B 的产出)
        var plan = Plan(4,
            Node("b", "生成数据", 0),
            Node("a", "基于 $node:b 的产出做汇总", 0));

        var run = Executor(order, waits).ExecuteAsync(plan).GetAwaiter().GetResult();

        Assert.Equal(["b", "a"], order);                                   // 先 B 后 A
        Assert.Equal(PlanNodeState.Completed, run.NodeStates["a"]);
        Assert.True(run.Waits.ContainsKey("a"));
        Assert.Equal("b", run.Waits["a"].ProducerId);
        Assert.Equal("queued", run.Waits["a"].Reason);                     // B 当时还没启动
        Assert.NotNull(run.Waits["a"].WaitUs);
        Assert.NotNull(run.Waits["a"].StartedWallUtcMs);          // v0.23.0 exp13 §3: 锚点与单调起点同写点落地
        Assert.True(run.Waits["a"].WallClockReconciled());        // 且本记录内不倒流 (跨进程可对账的前提)
        Assert.Contains(waits, w => w.Node == "a" && w.Producer == "b");    // 等待事件真出站
        Assert.Contains("b", plan.Nodes.First(n => n.Id == "a").RuntimeDeps); // 依赖已注入
        Assert.Single(run.Waits);              // 只有 a 在等
    }

    [Fact]
    public void A消费到的是B的真实产出_不是替代文本()
    {
        var ctx = new LocalNodeContext { SourceText = "用户原文", RemoteText = "远程正文" };
        ctx.NodeOutputs["b"] = "B的真实产出";
        var node = Node("a", "基于 $node:b 的产出做汇总", 0);
        node.RuntimeDeps.Add("b");
        node.DependsOn.Add("c");
        ctx.NodeOutputs["c"] = "C的产出";

        // 运行时依赖 (晚绑定, 更具体) 优先于声明依赖 —— 且绝不回落成用户原文
        Assert.Equal("B的真实产出", TextProcessExecutor.ResolveInput(node, ctx));
    }

    [Fact]
    public void B在等用户_A保持等待且计划暂停_不伪造数据()
    {
        var order = new List<string>();
        var waits = new List<(string Node, string Producer, string Reason)>();
        // B 不可执行 (待澄清, 无问询服务) → AwaitingClarification; A 在后一层, 引用 B
        var plan = Plan(4,
            Node("b", "生成数据", 0, executable: false),
            Node("a", "基于 $node:b 的产出做汇总", 1));

        var run = Executor(order, waits).ExecuteAsync(plan).GetAwaiter().GetResult();

        Assert.Equal(TaskPlanRunState.PausedForDependency, run.State);
        Assert.Equal(PlanNodeState.Waiting, run.NodeStates["a"]);
        Assert.Equal(PlanNodeState.AwaitingClarification, run.NodeStates["b"]);
        Assert.Equal("user", run.Waits["a"].Reason);
        Assert.DoesNotContain("a", order);                                  // A 没跑 (没数据不硬跑)
        Assert.Contains("等用户回复", run.PauseReason!);
        Assert.Contains(waits, w => w.Node == "a" && w.Reason == "user");
    }

    [Fact]
    public void B失败_等待中的A明确落终态_不静默兜底()
    {
        // 同层: A 先记账等待 (B 还没跑), B 随后失败 ⇒ A 必须明确落 Failed, 不许留悬空 Waiting
        var order = new List<string>();
        var waits = new List<(string Node, string Producer, string Reason)>();
        var plan = Plan(1,
            Node("b", "生成数据", 0),
            Node("a", "基于 $node:b 的产出做汇总", 0));

        var run = Executor(order, waits, (n, _) => new NodeExecutionResult
        {
            NodeId = n.Id,
            FinalState = n.Id == "b" ? PlanNodeState.Failed : PlanNodeState.Completed,
            FailureKind = NodeFailureKind.Permanent,
            Error = "b 挂了",
        }).ExecuteAsync(plan).GetAwaiter().GetResult();

        Assert.Equal(PlanNodeState.Failed, run.NodeStates["b"]);
        Assert.Equal(PlanNodeState.Failed, run.NodeStates["a"]);            // 明确 Failed (不是悬空 Waiting)
        Assert.DoesNotContain("a", order);                                  // A 的执行体从未被调用
        Assert.Contains("依赖未产出", run.PauseReason!);
    }

    [Fact]
    public void B在上一层失败_跨层连带跳过_仍不执行A()
    {
        var order = new List<string>();
        var waits = new List<(string Node, string Producer, string Reason)>();
        var plan = Plan(1,
            Node("b", "生成数据", 0),
            Node("a", "基于 $node:b 的产出做汇总", 1));

        var run = Executor(order, waits, (n, _) => new NodeExecutionResult
        {
            NodeId = n.Id,
            FinalState = n.Id == "b" ? PlanNodeState.Failed : PlanNodeState.Completed,
            FailureKind = NodeFailureKind.Permanent,
            Error = "b 挂了",
        }).ExecuteAsync(plan).GetAwaiter().GetResult();

        Assert.Equal(PlanNodeState.Failed, run.NodeStates["b"]);
        Assert.Contains(run.NodeStates["a"], new[] { PlanNodeState.Failed, PlanNodeState.Skipped });
        Assert.DoesNotContain("a", order);
        Assert.Contains("b 挂了", run.PauseReason!);
    }

    [Fact]
    public void 循环等待_死锁在记账时被拒()
    {
        var order = new List<string>();
        var waits = new List<(string Node, string Producer, string Reason)>();
        var plan = Plan(4,
            Node("a", "用 $node:b 的产出", 0),
            Node("b", "用 $node:a 的产出", 0));

        var run = Executor(order, waits).ExecuteAsync(plan).GetAwaiter().GetResult();

        Assert.Equal(TaskPlanRunState.Finished, run.State);
        Assert.Contains("成环", run.PauseReason!);
        Assert.Equal(PlanNodeState.Failed, run.NodeStates["b"]);            // 第二个记账的节点发现环
        Assert.DoesNotContain("a", order);
        Assert.DoesNotContain("b", order);
    }

    [Fact]
    public void 等待超上限_如实失败_不假设产出()
    {
        var order = new List<string>();
        var waits = new List<(string Node, string Producer, string Reason)>();
        var plan = Plan(1,
            Node("b", "生成数据", 0),
            Node("a", "用 $node:b 的产出", 0));

        // maxWaitMs=1: B 睡 60ms ⇒ A 的等待必然超限
        var executor = new TaskPlanExecutor(
            async (n, ct) =>
            {
                lock (order) order.Add(n.Id);
                if (n.Id == "b")
                    await Task.Delay(60, ct);
                return new NodeExecutionResult { NodeId = n.Id, FinalState = PlanNodeState.Completed, Output = "o" };
            },
            onWait: (n, p, r, ct) => Task.CompletedTask,
            maxWaitMs: 1);
        var run = executor.ExecuteAsync(plan).GetAwaiter().GetResult();

        Assert.Equal(PlanNodeState.Failed, run.NodeStates["a"]);
        Assert.Contains("超过上限", run.PauseReason!);
    }

    [Fact]
    public void 等待不占并发额度_额度为1也不死锁()
    {
        var order = new List<string>();
        var waits = new List<(string Node, string Producer, string Reason)>();
        var plan = Plan(1,
            Node("b", "生成数据", 0),
            Node("a", "用 $node:b 的产出", 0));

        var executor = new TaskPlanExecutor(
            async (n, ct) =>
            {
                lock (order) order.Add(n.Id);
                if (n.Id == "b") await Task.Delay(40, ct);
                return new NodeExecutionResult { NodeId = n.Id, FinalState = PlanNodeState.Completed, Output = "o" };
            },
            onWait: (n, p, r, ct) => Task.CompletedTask);
        var run = executor.ExecuteAsync(plan).GetAwaiter().GetResult();

        Assert.Equal(["b", "a"], order);                                    // 无死锁: B 先跑完, A 才跑
        Assert.Equal(TaskPlanRunState.Finished, run.State);
    }

    [Fact]
    public void 执行中才发现依赖_重复索要已注入依赖则如实失败()
    {
        var order = new List<string>();
        var waits = new List<(string Node, string Producer, string Reason)>();
        var plan = Plan(4,
            Node("a", "无文本引用 (依赖在执行中才发现)", 0),
            Node("b", "生成数据", 0));

        var run = Executor(order, waits, (n, _) => n.Id == "a"
            ? new NodeExecutionResult
            {
                NodeId = "a",
                FinalState = PlanNodeState.Waiting,
                NeedNodeId = "b",          // A 每次都要 b 的产出 (含注入之后)
            }
            : new NodeExecutionResult { NodeId = n.Id, FinalState = PlanNodeState.Completed, Output = "o" })
            .ExecuteAsync(plan).GetAwaiter().GetResult();

        Assert.Equal(PlanNodeState.Failed, run.NodeStates["a"]);
        Assert.Contains("重复索要", run.PauseReason!);
        Assert.True(order.Count(x => x == "a") >= 2);                       // 注入后重跑过一次
    }

    [Fact]
    public void 自引用与未知节点_不等待不空等()
    {
        var order = new List<string>();
        var waits = new List<(string Node, string Producer, string Reason)>();
        var plan = Plan(4,
            Node("a", "用 $node:a 的产出", 0),      // 自引用 = 配置错误 → 不等待
            Node("c", "用 $node:zzz 的产出", 0));   // 未知 id → 不等待

        var run = Executor(order, waits).ExecuteAsync(plan).GetAwaiter().GetResult();

        Assert.Empty(run.Waits);
        Assert.Equal(PlanNodeState.Completed, run.NodeStates["a"]);
        Assert.Equal(PlanNodeState.Completed, run.NodeStates["c"]);
        Assert.Equal(2, order.Count);
    }

    [Fact]
    public void 扫描器_只认显式契约_不猜自然语言()
    {
        var plan = new List<PlanNode>
        {
            Node("b", "生成数据", 0),
            Node("a", "任意", 0),
        };
        var self = plan[1];

        Assert.Equal("b", RuntimeDependencyScanner.FindProducer(
            Node("a", "基于 $node:b 的产出", 0), plan));
        Assert.Equal("b", RuntimeDependencyScanner.FindProducer(
            Node("a", "用 $dep:b 继续", 0), plan));
        Assert.Equal("b", RuntimeDependencyScanner.FindProducer(
            Node("a", "在 b 的产出上做统计", 0), plan));
        Assert.Null(RuntimeDependencyScanner.FindProducer(
            Node("a", "等它出结果后继续", 0), plan));      // 自然语言 → 不认 (不猜)
        Assert.Null(RuntimeDependencyScanner.FindProducer(
            Node("a", "用 $node:a 的产出", 0), plan));      // 自引用 → 不等 (plan 里只有 b 和自己)
        Assert.Null(RuntimeDependencyScanner.FindProducer(
            Node("a", "用 $node:zzz 的产出", 0), plan));
        Assert.Null(RuntimeDependencyScanner.FindProducer(self, plan));  // 自身文本无引用 → 不产生依赖
    }
}
