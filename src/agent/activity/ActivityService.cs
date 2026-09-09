using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;

namespace agent.activity;

/// <summary>v0.17.2-a (R336, 用户钦定): 活动条目 — 每活动 CLI 进程一条 (data/activity/&lt;pid&gt;.json 心跳)。</summary>
public sealed class ActivityEntry
{
    public int Pid { get; set; }
    public string WindowId { get; set; } = "cli";
    public string JobId { get; set; } = "";      // env AGENTFRAMEWORK_JOB_ID (Hermes cron job_id 等)
    public string AgentName { get; set; } = "main";
    public string TaskId { get; set; } = "";      // 当前 TaskCharter Id (running 时), 无则空
    public string TaskSummary { get; set; } = ""; // 当前任务/意图摘要
    public string Status { get; set; } = "running"; // running|idle|exiting
    public long StartedUnixMs { get; set; }
    public long LastHeartbeatUnixMs { get; set; }
}

/// <summary>
/// v0.17.2-a: 跨进程活动任务注册表 — 每个激活 CLI/agent 进程心跳写自己的 data/activity/&lt;pid&gt;.json
/// (v0.17.0 LockedFileWriter 原子写; 退出显式清或 10s 心跳过期被忽略)。查询 = 扫目录 (进程数 ≤ 几十,
/// 免 index 双写竞态)。支持: 本 CLI 之外其他 CLI/agent 任务状态可见 (窗口/job_id/pid/任务), 为
/// "如果当前没有其他任务存在则 X 后执行 Y" 条件调度提供 IsOtherAgentBusy 原语。
/// </summary>
public sealed class ActivityService
{
    private readonly string _dir;
    private readonly int _selfPid;
    private readonly string _windowId;
    private readonly string _jobId;
    private readonly string _agentName;
    private readonly long _expireMs;
    private ActivityEntry? _self;

    // 心跳过期阈值默认 90s — 心跳为轮级 (每轮 OnProcessAsync 首/尾各一), LLM 单轮可 30-60s,
    // 10s TTL 会误清在跑实例 (E2E 实证)。可用 env AGENTFRAMEWORK_ACTIVITY_EXPIRE_MS 覆盖 (E2E/调优)。
    private const int DefaultExpireMs = 90_000;
    private const int HeartbeatMs = 5_000; // 保留 (预留定时心跳, 当前轮级)

    public ActivityService(string? dataRoot = null, string? windowId = null, string? jobId = null,
        string? agentName = null, int? selfPid = null)
    {
        _dir = dataRoot is null
            ? Path.Combine(Environment.CurrentDirectory, "data", "activity")
            : Path.Combine(dataRoot, "activity");
        _selfPid = selfPid ?? Environment.ProcessId;
        _windowId = windowId ?? Environment.GetEnvironmentVariable("AGENTFRAMEWORK_WINDOW") ?? "cli";
        _jobId = jobId ?? Environment.GetEnvironmentVariable("AGENTFRAMEWORK_JOB_ID") ?? "";
        _agentName = agentName ?? Environment.GetEnvironmentVariable("AGENTFRAMEWORK_AGENT_NAME") ?? "main";
        var envMs = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_ACTIVITY_EXPIRE_MS");
        _expireMs = long.TryParse(envMs, out var parsed) && parsed > 0 ? parsed : DefaultExpireMs;
        Directory.CreateDirectory(_dir);
    }

    /// <summary>注册/更新自身心跳 (每轮调用; summary 截 120 字; 失败静默 — 活动感知不可阻塞主链)。</summary>
    public void Heartbeat(string? taskSummary = null, string? taskId = null, string status = "running")
    {
        try
        {
            _self ??= new ActivityEntry();
            _self.Pid = _selfPid;
            _self.WindowId = _windowId;
            _self.JobId = _jobId;
            _self.AgentName = _agentName;
            if (taskSummary is not null)
                _self.TaskSummary = taskSummary.Length > 120 ? taskSummary[..120] : taskSummary;
            if (taskId is not null) _self.TaskId = taskId;
            _self.Status = status;
            var now = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            _self.StartedUnixMs = _self.StartedUnixMs == 0 ? now : _self.StartedUnixMs;
            _self.LastHeartbeatUnixMs = now;
            var json = JsonSerializer.Serialize(_self, ActivityJsonCtx.Default.ActivityEntry);
            var path = PathFor(_selfPid);
            agent.execution.AtomicFileWriter.WriteAllText(path, json);
        }
        catch { /* 静默 */ }
    }

    public void MarkIdle() => Heartbeat(status: "idle");

    public void Clear()
    {
        try { var p = PathFor(_selfPid); if (File.Exists(p)) File.Delete(p); } catch { }
    }

    private string PathFor(int pid) => Path.Combine(_dir, $"{pid}.json");

    /// <summary>全部活动条目 (含自身), 过期 (心跳龄 &gt; 阈值, 默认 90s) 剔除并顺手清理死文件。</summary>
    public List<ActivityEntry> QueryActive()
    {
        var now = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        var result = new List<ActivityEntry>();
        try
        {
            foreach (var f in Directory.GetFiles(_dir, "*.json"))
            {
                try
                {
                    var e = JsonSerializer.Deserialize(File.ReadAllText(f), ActivityJsonCtx.Default.ActivityEntry);
                    if (e is null || e.Pid <= 0) continue;
                    if (now - e.LastHeartbeatUnixMs > _expireMs)
                    {
                        try { File.Delete(f); } catch { }
                        continue;
                    }
                    result.Add(e);
                }
                catch { try { File.Delete(f); } catch { } }
            }
        }
        catch { }
        return result.OrderBy(e => e.Pid).ToList();
    }

    /// <summary>除自身进程外是否有 running 活动 (其他 CLI/agent 正忙) — "无其他任务" 条件判定原语。</summary>
    public bool IsOtherAgentBusy()
    {
        var others = QueryActive().Where(e => e.Pid != _selfPid && e.Status == "running").ToList();
        return others.Count > 0;
    }

    /// <summary>渲染 (指令 /activity): 全部激活窗口/agent/任务/job_id/pid/心跳龄。</summary>
    public string Render()
    {
        var active = QueryActive();
        var others = active.Where(e => e.Pid != _selfPid).ToList();
        var self = active.FirstOrDefault(e => e.Pid == _selfPid);
        var sb = new System.Text.StringBuilder();
        sb.Append($"🗔 活动 agent ({active.Count}):");
        if (self is not null)
            sb.Append($"\n· [本进程] {self.AgentName} pid={self.Pid} win={self.WindowId} job={self.JobId} {self.Status} 任务: {Short(self.TaskSummary)}");
        foreach (var e in others)
        {
            var ageMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() - e.LastHeartbeatUnixMs;
            sb.Append($"\n· {e.AgentName} pid={e.Pid} win={e.WindowId} job={(!string.IsNullOrEmpty(e.JobId) ? e.JobId : "-")} {e.Status} (心跳 {ageMs / 1000}s前) 任务: {Short(e.TaskSummary)}");
        }
        if (others.Count == 0) sb.Append("\n(无其他活动 agent)");
        return sb.ToString();
    }

    private static string Short(string s) => string.IsNullOrEmpty(s) ? "-" : (s.Length > 60 ? s[..60] + "…" : s);
}

/// <summary>STJ source-gen context (AOT)。</summary>
[JsonSerializable(typeof(ActivityEntry))]
internal partial class ActivityJsonCtx : JsonSerializerContext;
