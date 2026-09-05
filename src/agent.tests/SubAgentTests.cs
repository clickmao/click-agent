using Xunit;
using Moq;
using Microsoft.Extensions.Logging;
using agent.subagent;
using agent.core;

namespace agent.tests;

/// <summary>
/// SubAgent / SubAgentPool 单元测试（针对真实实现）
/// </summary>
public class SubAgentTests
{
    private static SubAgent CreateAgent()
    {
        var loggerFactory = LoggerFactory.Create(b => b.SetMinimumLevel(LogLevel.Critical));
        return new SubAgent(loggerFactory.CreateLogger<SubAgent>());
    }

    private static IAgentContext CreateContext()
    {
        var sp = new Mock<IServiceProvider>();
        return new AgentContext(sp.Object)
        {
            SessionId = "test-session",
            UserId = "test-user"
        };
    }

    [Fact]
    public void SubAgent_ShouldHaveUniqueIds()
    {
        // Arrange & Act
        var agent1 = CreateAgent();
        var agent2 = CreateAgent();

        // Assert
        Assert.NotEqual(agent1.Id, agent2.Id);
        Assert.False(agent1.IsBusy);
        Assert.Null(agent1.CurrentTask);
    }

    [Fact]
    public async Task ExecuteAsync_BeforeInitialize_ShouldReturnError()
    {
        // Arrange
        var agent = CreateAgent();
        var task = new SubAgentTask { Name = "test", Description = "not initialized" };

        // Act
        var response = await agent.ExecuteAsync(task);

        // Assert
        Assert.False(response.Success);
        Assert.Contains("not initialized", response.Error ?? string.Empty, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task ExecuteAsync_AfterInitialize_ShouldCompleteTask()
    {
        // Arrange
        var agent = CreateAgent();
        var context = CreateContext();
        await agent.InitializeAsync(context);

        var task = new SubAgentTask
        {
            Name = "sample-task",
            Description = "Do something useful",
            Input = "sample input"
        };

        // Act
        var response = await agent.ExecuteAsync(task);

        // Assert
        Assert.True(response.Success);
        Assert.Equal(core.TaskStatus.Completed, task.Status);
        Assert.Equal(100, task.Progress);
        Assert.NotNull(task.Result);
        Assert.NotNull(task.CompletedAt);
        Assert.False(agent.IsBusy);
    }

    [Fact]
    public async Task ExecuteAsync_ShouldTrackExecutionTime()
    {
        // Arrange
        var agent = CreateAgent();
        await agent.InitializeAsync(CreateContext());

        var task = new SubAgentTask { Name = "timed-task" };

        // Act
        await agent.ExecuteAsync(task);

        // Assert
        Assert.True(task.ExecutionTimeMs >= 0);
        Assert.NotNull(task.StartedAt);
        Assert.NotNull(task.CompletedAt);
        Assert.True(task.CompletedAt >= task.StartedAt);
    }

    [Fact]
    public async Task ReportProgressAsync_ShouldUpdateCurrentTaskProgress()
    {
        // Arrange
        var agent = CreateAgent();
        await agent.InitializeAsync(CreateContext());
        var progressEvents = new List<double>();
        agent.ProgressChanged += (_, p) => progressEvents.Add(p);

        // Act - 先手动执行一个任务让 CurrentTask 非空
        var task = new SubAgentTask { Name = "progress-task" };
        var executeTask = agent.ExecuteAsync(task);

        // 等待完成
        await executeTask;

        // Assert - 执行过程中会报告多个进度（10/30/60/90/100）
        Assert.Contains(10, progressEvents);
        Assert.Contains(90, progressEvents);
    }

    [Fact]
    public async Task SubAgentPool_AcquireRelease_ShouldReuseAgents()
    {
        // Arrange
        var loggerFactory = LoggerFactory.Create(b => b.SetMinimumLevel(LogLevel.Critical));
        var pool = new SubAgentPool(loggerFactory.CreateLogger<SubAgentPool>(), maxAgents: 2);

        // Act
        var agent1 = await pool.AcquireAsync();
        await pool.ReleaseAsync(agent1);
        var agent2 = await pool.AcquireAsync();

        // Assert
        Assert.NotNull(agent1);
        Assert.NotNull(agent2);
        Assert.Equal(agent1.Id, agent2.Id); // 释放后复用
    }

    [Fact]
    public void SubAgentPool_MaxAgents_ShouldBeConfigurable()
    {
        // Arrange & Act
        var loggerFactory = LoggerFactory.Create(b => b.SetMinimumLevel(LogLevel.Critical));
        var pool = new SubAgentPool(loggerFactory.CreateLogger<SubAgentPool>(), maxAgents: 7);

        // Assert
        Assert.Equal(7, pool.MaxAgents);
    }
}
