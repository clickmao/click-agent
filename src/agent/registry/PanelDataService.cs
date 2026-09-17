using System.Text.Json;
using System.Text.Json.Serialization;
using agent.session;

namespace agent.registry;

/// <summary>
/// 面板数据服务 (v7.14): /status 与 /session 家族命令的 JSON 数据出口。
/// 铁律: 输出全部为格式化 JSON (程序可解析), 不做人类可读面板 (渲染归客户端)。
/// 数据源: SessionManager (内存态) + JsonSessionMemoryStore (落盘态) + AgentProfileStore + CapabilityScanner。
/// </summary>
public sealed class PanelDataService
{
    private readonly ISessionManager _sessions;
    private readonly JsonSessionMemoryStore _memoryStore;
    private readonly AgentProfileStore _profiles;
    private readonly CapabilityScanner _capabilities;
    private readonly string _dataPath;

    private readonly agent.recovery.CheckpointStore _checkpoints;

    public PanelDataService(
        ISessionManager sessions,
        JsonSessionMemoryStore memoryStore,
        AgentProfileStore profiles,
        CapabilityScanner capabilities,
        string dataPath = "data",
        agent.recovery.CheckpointStore? checkpoints = null)
    {
        _sessions = sessions;
        _memoryStore = memoryStore;
        _profiles = profiles;
        _capabilities = capabilities;
        _dataPath = dataPath;
        _checkpoints = checkpoints ?? new agent.recovery.CheckpointStore(dataPath);
    }

    /// <summary>
    /// /status (全局): 轮次无关的全局快照 — 能力清单/agent 总数/会话总数/偏好摘要。
    /// </summary>
    public string RenderGlobalStatus(int turnCount, string? lastIntent, string? forecastTendency,
        IReadOnlyList<string>? preferenceSummary)
    {
        var all = _sessions.GetAllSessionsAsync().GetAwaiter().GetResult().ToList();
        var caps = _capabilities.Snapshot();
        var payload = new GlobalStatusPanel
        {
            TurnCount = turnCount,
            LastIntent = lastIntent,
            ForecastTendency = forecastTendency,
            PreferenceSummary = preferenceSummary?.ToList() ?? new List<string>(),
            SessionCount = all.Count,
            AgentCount = _capabilities.Count,
            Capabilities = caps.Select(c => new CapabilityEntry
            {
                Name = c.Name, Description = c.Description, Source = c.Source,
            }).ToList(),
        };

        // 需求3: 主会话检查点恢复裁定 (cli-main 会话; 无检查点 → null 不输出)
        var checkpoint = _checkpoints.Load("cli-main");
        if (checkpoint != null)
        {
            var recovery = agent.recovery.CheckpointRecovery.BuildRecoveryPlan(checkpoint);
            payload.Recovery = new RecoveryPanel
            {
                Resumable = recovery.Resumable,
                PlanId = recovery.PlanId,
                ResumeFromNodeId = recovery.ResumeFromNodeId,
                CompletedNodes = recovery.CompletedNodeIds.Count,
                Summary = recovery.Summary,
            };
        }

        return System.Text.Json.JsonSerializer.Serialize(payload, PanelJsonContext.Default.GlobalStatusPanel);;
    }

    /// <summary>
    /// /status &lt;agent_uid&gt;: 指定 agent 的上下文长度/画像/长期记忆 (JSON)。
    /// </summary>
    public string RenderAgentStatus(string agentUid)
    {
        var profile = _profiles.GetOrCreate(agentUid);
        var sessions = _sessions.GetAllSessionsAsync().GetAwaiter().GetResult()
            .Where(s => s.UserId == agentUid || s.Id == agentUid)
            .ToList();
        // v7.14: uid≠sessionId — 记忆按"该 uid 全部落盘会话"聚合 (最近活跃会话为主显示, 计入上下文口径)
        agent.session.SessionMemory? memory = null;
        var diskIds = new List<string>();
        try { diskIds = _memoryStore.EnumerateSessionIds().ToList(); } catch { /* 目录缺失 → 空 */ }
        var liveIds = sessions.Select(s => s.Id).ToHashSet(StringComparer.Ordinal);
        var memIds = liveIds.Concat(diskIds).Distinct().ToList();
        foreach (var id in memIds)
        {
            var m = _memoryStore.Load(id);
            if (m == null || string.IsNullOrEmpty(m.LongTermMemory))
                continue;
            if (memory == null || m.UpdatedAt > memory.UpdatedAt)
                memory = m; // 取最近更新的会话记忆作为主显示
        }
        // 上下文长度: 该 agent 关联会话的消息总量 + 记忆块长度 (字符口径, 程序可算)
        var contextChars = sessions.Sum(s => s.Messages.Sum(m => m.Content?.Length ?? 0))
                           + (memory?.LongTermMemory.Length ?? 0);
        var payload = new AgentStatusPanel
        {
            AgentUid = agentUid,
            Exists = sessions.Count > 0 || memory != null,
            ContextChars = contextChars,
            SessionCount = sessions.Count,
            Profile = new ProfileEntry
            {
                DecisionStyle = profile.DecisionStyle,
                OutputStyle = profile.OutputStyle,
                MaxRetries = profile.MaxRetries,
                PreferClarifyFirst = profile.PreferClarifyFirst,
                TaskSuccess = profile.TaskSuccess,
                TaskFailure = profile.TaskFailure,
                ToolAffinity = profile.ToolAffinity,
            },
            LongTermMemory = memory?.LongTermMemory ?? string.Empty,
            MemoryMaxChars = memory?.MaxChars ?? SessionMemory.DefaultMaxChars,
            Goal = memory?.Goal == null ? null : new GoalEntry
            {
                GoalText = memory.Goal.GoalText,
                KeyEntities = memory.Goal.KeyEntities,
                Constraints = memory.Goal.Constraints,
                Milestones = memory.Goal.Milestones,
            },
        };
        return System.Text.Json.JsonSerializer.Serialize(payload, PanelJsonContext.Default.AgentStatusPanel);;
    }

    /// <summary>
    /// /session &lt;agent_uid&gt;: 该 agent 的历史会话数量与摘要 (JSON)。
    /// </summary>
    public string RenderSessionList(string agentUid)
    {
        var sessions = CollectSessions(agentUid);
        var payload = new SessionListPanel
        {
            AgentUid = agentUid,
            SessionCount = sessions.Count,
            Sessions = sessions.Select((s, i) => new SessionSummaryEntry
            {
                Index = i,
                SessionId = s.Id,
                UserId = s.UserId,
                TurnCount = s.TurnCount,
                MessageCount = s.Messages.Count,
                LastActivityAt = s.LastActivityAt,
                Preview = BuildPreview(s),
            }).ToList(),
        };
        return System.Text.Json.JsonSerializer.Serialize(payload, PanelJsonContext.Default.SessionListPanel);;
    }

    /// <summary>
    /// /session &lt;agent_uid&gt; &lt;index&gt;: 指定索引历史会话详情 (JSON)。
    /// </summary>
    public string RenderSessionDetail(string agentUid, int index)
    {
        var sessions = CollectSessions(agentUid);
        var payload = new SessionDetailPanel { AgentUid = agentUid, RequestedIndex = index };
        if (index < 0 || index >= sessions.Count)
        {
            payload.Found = false;
            payload.Error = $"索引越界: 有效范围 0..{sessions.Count - 1}";
            return System.Text.Json.JsonSerializer.Serialize(payload, PanelJsonContext.Default.SessionDetailPanel);;
        }
        var s = sessions[index];
        payload.Found = true;
        payload.SessionId = s.Id;
        payload.UserId = s.UserId;
        payload.TurnCount = s.TurnCount;
        payload.CreatedAt = s.CreatedAt;
        payload.LastActivityAt = s.LastActivityAt;
        payload.Memory = _memoryStore.Load(s.Id)?.LongTermMemory ?? string.Empty;
        payload.Goal = _memoryStore.Load(s.Id)?.Goal?.GoalText;
        payload.Messages = s.Messages.Select(m => new MessageEntry
        {
            Role = m.Role.ToString(),
            SenderId = m.SenderId,
            Content = m.Content ?? string.Empty,
            Timestamp = m.Timestamp,
        }).ToList();
        return System.Text.Json.JsonSerializer.Serialize(payload, PanelJsonContext.Default.SessionDetailPanel);;
    }

    private List<Session> CollectSessions(string agentUid)
    {
        // 内存态 + 落盘态合并 (重启后内存为空, 落盘的记忆文件兜底成"摘要级"会话)
        var live = _sessions.GetAllSessionsAsync().GetAwaiter().GetResult()
            .Where(s => s.UserId == agentUid || s.Id == agentUid)
            .ToList();
        var result = live.ToList();
        var liveIds = live.Select(s => s.Id).ToHashSet(StringComparer.Ordinal);
        // 落盘会话 (无内存态): 从 memory store 读回摘要行
        foreach (var diskId in _memoryStore.EnumerateSessionIds())
        {
            if (liveIds.Contains(diskId))
                continue;
            var m = _memoryStore.Load(diskId);
            if (m == null)
                continue;
            result.Add(new Session
            {
                Id = diskId,
                UserId = agentUid,
                TurnCount = m.EntryCount,
            });
        }
        return result.OrderByDescending(s => s.LastActivityAt).ToList();
    }

    private static string BuildPreview(Session s)
    {
        var lastUser = s.Messages.LastOrDefault(m => m.Role == core.MessageRole.User);
        if (lastUser?.Content != null)
            return lastUser.Content.Length > 80 ? lastUser.Content[..80] + "…" : lastUser.Content;
        var any = s.Messages.LastOrDefault();
        if (any?.Content != null)
            return any.Content.Length > 80 ? any.Content[..80] + "…" : any.Content;
        return "(落盘会话 — 无消息快照)";
    }
}
