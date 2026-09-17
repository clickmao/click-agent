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
