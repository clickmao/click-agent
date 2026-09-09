using System;
using System.IO;
using System.Linq;
using Xunit;
using agent.activity;

namespace agentframework.tests;

/// <summary>v0.17.2-a (R336): 活动任务注册表 — 心跳注册 / 查询 / 过期 / 自身排除 / 条件原语 / 渲染。</summary>
public class ActivityServiceTests
{
    private static string TempDir()
    {
        var d = Path.Combine(Path.GetTempPath(), "af-act-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(d);
        return d;
    }


    [Fact]
    public void Heartbeat_RegistersSelf_QuerySeesIt()
    {
        var dir = TempDir();
        var svc = new ActivityService(dir, windowId: "win-test", jobId: "job-42", selfPid: 9001);
        svc.Heartbeat("做一个 Web API", taskId: "tc123");
        var active = svc.QueryActive();
        Assert.Contains(active, e => e.Pid == 9001);
        var self = active.First(e => e.Pid == 9001);
        Assert.Equal("win-test", self.WindowId);
        Assert.Equal("job-42", self.JobId);
        Assert.Equal("tc123", self.TaskId);
        Assert.Contains("Web API", self.TaskSummary);
    }

    [Fact]
    public void Expiry_StaleEntry_ExcludedAndCleaned()
    {
        var dir = TempDir();
        // 模拟另一个进程的过期条目 (旧心跳时间):
        var svc = new ActivityService(dir, selfPid: 9001);
        svc.Heartbeat("self");
        var other = new ActivityEntry
        {
            Pid = 7777, WindowId = "other", JobId = "job-old", AgentName = "other",
            Status = "running",
            StartedUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() - 120_000,
            LastHeartbeatUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() - 120_000, // 过期
        };
        var json = System.Text.Json.JsonSerializer.Serialize(other);
        File.WriteAllText(Path.Combine(dir, "activity", "7777.json"), json);
        var active = svc.QueryActive();
        Assert.DoesNotContain(active, e => e.Pid == 7777);
        Assert.False(File.Exists(Path.Combine(dir, "activity", "7777.json")), "过期文件应被清理");
    }

    [Fact]
    public void IsOtherAgentBusy_SelfExcluded()
    {
        var dir = TempDir();
        var svc = new ActivityService(dir, selfPid: 9001);
        svc.Heartbeat("我自己的任务");
        Assert.False(svc.IsOtherAgentBusy(), "只有自身 → 无其他任务");
        // 注入另一 running 进程:
        var other = new ActivityEntry
        {
            Pid = 8001, WindowId = "cli2", JobId = "job-x", AgentName = "main",
            Status = "running",
            StartedUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
            LastHeartbeatUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
        };
        File.WriteAllText(Path.Combine(dir, "activity", "8001.json"),
            System.Text.Json.JsonSerializer.Serialize(other));
        Assert.True(svc.IsOtherAgentBusy(), "有另一 running → 忙");
    }

    [Fact]
    public void MultipleAgents_IndependentHeartbeats_NoCrossTalk()
    {
        var dir = TempDir();
        var a = new ActivityService(dir, windowId: "wA", selfPid: 1001);
        var b = new ActivityService(dir, windowId: "wB", selfPid: 1002);
        a.Heartbeat("任务A");
        b.Heartbeat("任务B");
        var active = new ActivityService(dir, selfPid: 9999).QueryActive();
        Assert.Equal(2, active.Count(e => e.Pid is 1001 or 1002));
        var ea = active.First(e => e.Pid == 1001);
        var eb = active.First(e => e.Pid == 1002);
        Assert.Equal("任务A", ea.TaskSummary);
        Assert.Equal("任务B", eb.TaskSummary);
    }

    [Fact]
    public void Render_IncludesOtherAgentJobId()
    {
        var dir = TempDir();
        var svc = new ActivityService(dir, jobId: "self-job", selfPid: 9001);
        svc.Heartbeat("self task");
        var other = new ActivityEntry
        {
            Pid = 8002, WindowId = "cli-other", JobId = "cron-abc", AgentName = "main",
            Status = "running",
            StartedUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
            LastHeartbeatUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
        };
        File.WriteAllText(Path.Combine(dir, "activity", "8002.json"),
            System.Text.Json.JsonSerializer.Serialize(other));
        var text = svc.Render();
        Assert.Contains("cron-abc", text);   // job_id 可见
        Assert.Contains("8002", text);       // pid 可见
        Assert.Contains("cli-other", text);  // 窗口可见
    }

    [Fact]
    public void Clear_ExitCleanup_RemovesOwnFile()
    {
        var dir = TempDir();
        var svc = new ActivityService(dir, selfPid: 9001);
        svc.Heartbeat("要退出的任务");
        var ownFile = Path.Combine(dir, "activity", "9001.json");
        Assert.True(File.Exists(ownFile), "心跳后应存在自身文件");
        svc.Clear();
        Assert.False(File.Exists(ownFile), "Clear 应删除自身活动文件 (退出清理)");
        Assert.Empty(svc.QueryActive());
        svc.Clear(); // 幂等 — 不抛
    }

    [Fact]
    public void IsOtherAgentBusy_IdleOther_NotBusy()
    {
        var dir = TempDir();
        var svc = new ActivityService(dir, selfPid: 9001);
        svc.Heartbeat("自己");
        var idle = new ActivityEntry
        {
            Pid = 8003, WindowId = "cli2", AgentName = "main", Status = "idle",
            StartedUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
            LastHeartbeatUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
        };
        File.WriteAllText(Path.Combine(dir, "activity", "8003.json"),
            System.Text.Json.JsonSerializer.Serialize(idle));
        Assert.False(svc.IsOtherAgentBusy(), "idle 其他 agent 不算忙 — 条件调度可执行");
    }

    [Fact]
    public void ConcurrentHeartbeats_DifferentPids_NoCrossTalk()
    {
        var dir = TempDir();
        var a = new ActivityService(dir, windowId: "wA", selfPid: 1001);
        var b = new ActivityService(dir, windowId: "wB", selfPid: 1002);
        var errs = new System.Collections.Concurrent.ConcurrentQueue<Exception>();
        // 双写者各自高频心跳 (模拟双进程并发) — 各自 pid 文件互不覆盖
        Parallel.For(0, 2, new ParallelOptions { MaxDegreeOfParallelism = 2 }, i =>
        {
            try
            {
                if (i == 0)
                    for (var n = 0; n < 50; n++) { a.Heartbeat($"任务A-{n}"); }
                else
                    for (var n = 0; n < 50; n++) { b.Heartbeat($"任务B-{n}"); }
            }
            catch (Exception ex) { errs.Enqueue(ex); }
        });
        Assert.Empty(errs);
        var active = new ActivityService(dir, selfPid: 9999).QueryActive();
        Assert.Equal(2, active.Count(e => e.Pid is 1001 or 1002));
        var ea = active.First(e => e.Pid == 1001);
        var eb = active.First(e => e.Pid == 1002);
        Assert.True(ea.TaskSummary.StartsWith("任务A", StringComparison.Ordinal), $"A 摘要被串扰: {ea.TaskSummary}");
        Assert.True(eb.TaskSummary.StartsWith("任务B", StringComparison.Ordinal), $"B 摘要被串扰: {eb.TaskSummary}");
    }

    [Fact]
    public void ExpireMs_EnvOverride_Applied()
    {
        var dir = TempDir();
        var prev = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_ACTIVITY_EXPIRE_MS");
        try
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_ACTIVITY_EXPIRE_MS", "3000");
            var svc = new ActivityService(dir, selfPid: 9001);
            svc.Heartbeat("self");
            var stale = new ActivityEntry
            {
                Pid = 7011, WindowId = "other", Status = "running",
                StartedUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() - 10_000,
                LastHeartbeatUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() - 10_000,
            };
            File.WriteAllText(Path.Combine(dir, "activity", "7011.json"),
                System.Text.Json.JsonSerializer.Serialize(stale));
            Assert.DoesNotContain(svc.QueryActive(), e => e.Pid == 7011);
        }
        finally
        {
            Environment.SetEnvironmentVariable("AGENTFRAMEWORK_ACTIVITY_EXPIRE_MS", prev);
        }
    }

    [Fact]
    public void Heartbeat_FailureSilent_CorruptFileTolerated()
    {
        var dir = TempDir();
        var activityDir = Path.Combine(dir, "activity");
        Directory.CreateDirectory(activityDir);
        File.WriteAllText(Path.Combine(activityDir, "bad.json"), "{corrupt"); // 损坏文件必须位于扫描目录内
        var svc = new ActivityService(dir, selfPid: 9001);
        svc.Heartbeat("ok"); // 不抛
        var active = svc.QueryActive(); // 损坏文件被容错跳过并清理, 自身条目仍在
        Assert.Single(active);
        Assert.Equal(9001, active[0].Pid);
        Assert.False(File.Exists(Path.Combine(activityDir, "bad.json")), "损坏文件应被容错清理");
    }
}
