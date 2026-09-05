using System.IO;
using agent.recovery;
using agent.intent;
using agent.registry;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 需求3 测试: 会话中断恢复 — 检查点原子落盘/损坏容忍/恢复裁定/执行器接线。
/// </summary>
public class CheckpointRecoveryTests : IDisposable
{
    private readonly string _dir;

    public CheckpointRecoveryTests()
    {
        _dir = Path.Combine(Path.GetTempPath(), "ckpt_tests_" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(_dir);
    }

    public void Dispose()
    {
        try { Directory.Delete(_dir, recursive: true); } catch { /* 清理失败不影响断言 */ }
    }

    [Fact]
    public void Save_And_Load_Roundtrip()
    {
        var store = new CheckpointStore(_dir);
        store.Save(new ExecutionCheckpoint
        {
            SessionId = "s1",
            PlanId = "plan-1",
            RunId = "run-1",
            NodeStates = new System.Collections.Generic.Dictionary<string, string>
            {
                ["n1"] = "Completed", ["n2"] = "Pending", ["n3"] = "Pending",
            },
            LastCompletedNodeId = "n1",
        });

        var loaded = store.Load("s1");
        Assert.NotNull(loaded);
        Assert.Equal("plan-1", loaded!.PlanId);
        Assert.Equal(3, loaded.NodeStates.Count);
        Assert.Equal("n1", loaded.LastCompletedNodeId);
    }

    [Fact]
    public void Corrupted_File_Returns_Null_Not_Throw()
    {
        var store = new CheckpointStore(_dir);
        System.IO.Directory.CreateDirectory(Path.Combine(_dir, "sessions", "s2"));
        File.WriteAllText(Path.Combine(_dir, "sessions", "s2", "checkpoint.json"), "{半截json...");
        Assert.Null(store.Load("s2"));
    }

    [Fact]
    public void Recovery_Resumes_At_First_Pending_Node()
    {
        var checkpoint = new ExecutionCheckpoint
        {
            SessionId = "s1",
            PlanId = "plan-1",
            NodeStates = new System.Collections.Generic.Dictionary<string, string>
            {
                ["n1"] = "Completed", ["n2"] = "Completed",
                ["n3"] = "Running", ["n4"] = "Pending",
            },
        };
        var plan = CheckpointRecovery.BuildRecoveryPlan(checkpoint);

        Assert.True(plan.Resumable);
        Assert.Equal("n3", plan.ResumeFromNodeId); // Running 视为重跑起点
        Assert.Equal(2, plan.CompletedNodeIds.Count);
        Assert.Contains("n3", plan.Summary);
    }

    [Fact]
    public void Recovery_All_Completed_Is_Not_Resumable()
    {
        var checkpoint = new ExecutionCheckpoint
        {
            SessionId = "s1", PlanId = "plan-9",
            NodeStates = new System.Collections.Generic.Dictionary<string, string>
            {
                ["n1"] = "Completed", ["n2"] = "Completed",
            },
        };
        var plan = CheckpointRecovery.BuildRecoveryPlan(checkpoint);
        Assert.False(plan.Resumable);
        Assert.DoesNotContain("继续", plan.Summary.Split(' ')[0]); // 摘要语义: 无需恢复
    }

    [Fact]
    public void Clear_Removes_Checkpoint()
    {
        var store = new CheckpointStore(_dir);
        store.Save(new ExecutionCheckpoint { SessionId = "s3", PlanId = "p" });
        Assert.NotNull(store.Load("s3"));
        store.Clear("s3");
        Assert.Null(store.Load("s3"));
    }

    [Fact]
    public void Executor_Writes_Checkpoint_At_Level_Boundaries()
    {
        var store = new CheckpointStore(_dir);
        var plan = new TaskPlan
        {
            PlanId = "plan-ck",
            SourceText = "测试计划",
            Nodes = new System.Collections.Generic.List<PlanNode>
            {
                new() { Id = "a", Text = "a", Level = 0, DependsOn = new System.Collections.Generic.List<string>() },
                new() { Id = "b", Text = "b", Level = 0, DependsOn = new System.Collections.Generic.List<string>() },
                new() { Id = "c", Text = "c", Level = 1, DependsOn = new System.Collections.Generic.List<string> { "a", "b" } },
            },
        };
        var executor = new TaskPlanExecutor(
            (node, _) => System.Threading.Tasks.Task.FromResult(new NodeExecutionResult
            {
                NodeId = node.Id, FinalState = PlanNodeState.Completed,
            }),
            checkpointStore: store,
            checkpointSessionId: "s-exec");

        var run = executor.ExecuteAsync(plan).GetAwaiter().GetResult();
        Assert.Equal(TaskPlanRunState.Finished, run.State);

        var ck = store.Load("s-exec");
        Assert.NotNull(ck);
        Assert.Equal("plan-ck", ck!.PlanId);
        Assert.All(ck.NodeStates.Values, v => Assert.Equal("Completed", v));
    }
}
