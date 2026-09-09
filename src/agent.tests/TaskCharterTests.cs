using agent.tasks;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v0.15.1-a TaskCharter 单测: 状态机/持久化往返/归档/损坏容忍。
/// </summary>
public class TaskCharterTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), $"tc-{Guid.NewGuid():N}");

    public void Dispose()
    {
        if (Directory.Exists(_root)) Directory.Delete(_root, recursive: true);
    }

    [Fact]
    public void Save_Load_RoundTrip()
    {
        var c = new TaskCharter
        {
            GoalText = "实现用户登录接口",
            KeyEntities = { "登录", "接口" },
            Status = "running",
            AcceptanceCriteria = { "测试通过", "构建零警告" },
        };
        c.Save(_root);
        var loaded = TaskCharter.LoadActive(_root);
        Assert.NotNull(loaded);
        Assert.Equal("实现用户登录接口", loaded!.GoalText);
        Assert.Equal("running", loaded.Status);
        Assert.Contains("登录", loaded.KeyEntities);
    }

    [Fact]
    public void IsRunning_PlanningAndRunning_True()
    {
        Assert.True(new TaskCharter { Status = "planning" }.IsRunning);
        Assert.True(new TaskCharter { Status = "running" }.IsRunning);
        Assert.False(new TaskCharter { Status = "done" }.IsRunning);
        Assert.False(new TaskCharter { Status = "failed" }.IsRunning);
    }

    [Fact]
    public void LoadActive_NoFile_Null()
    {
        Assert.Null(TaskCharter.LoadActive(_root));
    }

    [Fact]
    public void LoadActive_CorruptFile_Null()
    {
        Directory.CreateDirectory(_root);
        Directory.CreateDirectory(Path.Combine(_root, "task-charters"));
        File.WriteAllText(TaskCharter.ActivePath(_root), "{broken");
        Assert.Null(TaskCharter.LoadActive(_root));
    }

    [Fact]
    public void Archive_MovesActiveToFinalStatus()
    {
        var c = new TaskCharter { GoalText = "x" };
        c.Save(_root);
        c.Archive(_root, "done");
        Assert.Equal("done", c.Status);
        Assert.Null(TaskCharter.LoadActive(_root)); // 活动位已清
        Assert.True(File.Exists(Path.Combine(_root, "task-charters", $"{c.Id}-done.json")));
        // R322b: 归档文件内容 = 终态快照 (Status 写入 + pending 清空)
        var archived = System.Text.Json.JsonSerializer.Deserialize(
            File.ReadAllText(Path.Combine(_root, "task-charters", $"{c.Id}-done.json")),
            TaskCharterJsonCtx.Default.TaskCharter);
        Assert.Equal("done", archived!.Status);
        Assert.Empty(archived.PendingInputs);
    }

    [Fact]
    public void PendingInputs_Append_Persists()
    {
        var c = new TaskCharter { GoalText = "x", Status = "running" };
        c.PendingInputs.Add("顺便把日志级别调成 warning");
        c.Save(_root);
        var loaded = TaskCharter.LoadActive(_root)!;
        Assert.Single(loaded.PendingInputs);
    }
}
