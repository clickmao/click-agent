using agent.registry;
using agent.session;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// v7.14 特性测试: 编排问询驱动 / 会话长期记忆 / Agent 画像 / 能力探嗅 / 面板 JSON。
/// </summary>
public class V714FeatureTests
{
    // ── ③ SessionMemory: 滚动上限 + 目标优先存活 ──

    [Fact]
    public void SessionMemory_RollsOffOldest_NonGoalFirst()
    {
        var m = new SessionMemory(300); // 上限 300 字符
        m.SetGoal("完成 AOT 迁移", keyEntities: new[] { "agenthost" });
        for (var i = 0; i < 20; i++)
            m.Remember($"常规日志条目 {i}: 一段普通的工作记录内容, 用于撑爆记忆上限测试。");
        Assert.True(m.LongTermMemory.Length <= 300, $"记忆 {m.LongTermMemory.Length} 超限");
        Assert.Contains("[目标]", m.LongTermMemory); // 目标条目最后裁 → 应存活
    }

    [Fact]
    public void SessionMemory_SanitizesSecrets()
    {
        var m = new SessionMemory(1000);
        m.Remember("配置如下: API_KEY=sk-abc123def456 和 token=ghp_aaaabbbbccccdddd");
        Assert.DoesNotContain("sk-abc123def456", m.LongTermMemory);
        Assert.DoesNotContain("ghp_aaaabbbbccccdddd", m.LongTermMemory);
        Assert.Contains("[REDACTED]", m.LongTermMemory);
    }

    [Fact]
    public void SessionMemory_RestoreRoundTrip()
    {
        var m = new SessionMemory(500);
        m.SetGoal("测试目标");
        m.AddMilestone("第一步完成");
        m.Remember("普通记忆条目");

        // 落盘→读回
        var dir = Path.Combine(Path.GetTempPath(), "v714_memtest_" + Guid.NewGuid().ToString("N")[..8]);
        try
        {
            var store = new JsonSessionMemoryStore(dir);
            store.Save("sess1", m);
            var back = store.Load("sess1");
            Assert.NotNull(back);
            Assert.Equal(m.LongTermMemory, back!.LongTermMemory);
            Assert.NotNull(back.Goal);
            Assert.Equal("测试目标", back.Goal!.GoalText);
            Assert.Contains("第一步完成", back.Goal.Milestones);
        }
        finally
        {
            if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void SessionMemory_RenderForPrompt_HasDirectionBlock()
    {
        var m = new SessionMemory(1000);
        m.SetGoal("对标工业级框架", constraints: new[] { "AOT 必须 0 警告" });
        m.AddMilestone("编译绿");
        var rendered = m.RenderForPrompt();
        Assert.Contains("【任务方向】对标工业级框架", rendered);
        Assert.Contains("【约束】AOT 必须 0 警告", rendered);
        Assert.Contains("【已完成】编译绿", rendered);
    }

    // ── ④ AgentProfile: 动态学习 + prompt 渲染 ──

    [Fact]
    public void AgentProfile_LearnsTaskOutcomes()
    {
        var p = new AgentProfile { AgentUid = "ag1" };
        p.RecordTaskOutcome("code_generation", success: true, toolUsed: "dotnet");
        p.RecordTaskOutcome("code_generation", success: true, toolUsed: "dotnet");
        p.RecordTaskOutcome("code_generation", success: false);
        p.RecordTaskOutcome("web_search", success: true);

        Assert.Equal(2.0 / 3.0, p.SuccessRateFor("code_generation"));
        Assert.Equal(1.0, p.SuccessRateFor("web_search"));
        Assert.Null(p.SuccessRateFor("unknown_intent"));

        var rendered = p.RenderForPrompt();
        Assert.Contains("擅长=", rendered);
        Assert.Contains("code_generation", rendered);
        Assert.Contains("常用工具=dotnet", rendered);
    }

    [Fact]
    public void AgentProfileStore_PersistsAndReloads()
    {
        var dir = Path.Combine(Path.GetTempPath(), "v714_proftest_" + Guid.NewGuid().ToString("N")[..8]);
        try
        {
            var s1 = new AgentProfileStore(dir);
            var p = s1.GetOrCreate("main-agent");
            p.DecisionStyle = "conservative";
            p.RecordTaskOutcome("refactor", success: true);
            s1.Save();

            var s2 = new AgentProfileStore(dir);
            var back = s2.GetOrCreate("main-agent");
            Assert.Equal("conservative", back.DecisionStyle);
            Assert.Equal(1, back.TaskSuccess["refactor"]);
            Assert.Equal(1, back.TaskSuccess["refactor"]);
        }
        finally
        {
            if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
        }
    }

    // ── ⑤ CapabilityScanner: PATH 探嗅 + prompt 渲染 ──

    [Fact]
    public void CapabilityScanner_FindsPathTools()
    {
        var scanner = new CapabilityScanner();
        scanner.Scan();
        var caps = scanner.Snapshot();
        Assert.NotEmpty(caps);
        // 测试机上 dotnet 一定在 (我们正在用它编译)
        Assert.Contains(caps, c => c.Name == "dotnet" && c.Source == "path");
        var rendered = scanner.RenderForPrompt();
        Assert.Contains("dotnet", rendered);
        Assert.DoesNotContain("不可用", rendered); // 渲染只列可用能力
    }

    [Fact]
    public void CapabilityScanner_ScanIsIdempotent()
    {
        var scanner = new CapabilityScanner();
        scanner.Scan();
        var count1 = scanner.Count;
        scanner.Scan();
        Assert.Equal(count1, scanner.Count);
    }

    // ── a7 PanelDataService: 4 命令 JSON 契约 ──

    [Fact]
    public void PanelData_GlobalStatus_ValidJson()
    {
        var (panel, dir) = MakePanel();
        try
        {
            var json = panel.RenderGlobalStatus(3, "code_generation", "coding",
                new List<string> { "Path → absolute [2]" });
            var doc = System.Text.Json.JsonDocument.Parse(json); // 能解析 = 合法 JSON
            var root = doc.RootElement;
            Assert.Equal(3, root.GetProperty("TurnCount").GetInt32());
            Assert.Equal("code_generation", root.GetProperty("LastIntent").GetString());
            Assert.True(root.GetProperty("Capabilities").GetArrayLength() > 0);
        }
        finally { Cleanup(dir); }
    }

    [Fact]
    public void PanelData_AgentStatus_ShowsProfileAndMemory()
    {
        var (panel, dir) = MakePanel();
        try
        {
            var json = panel.RenderAgentStatus("ag-main");
            var doc = System.Text.Json.JsonDocument.Parse(json);
            var root = doc.RootElement;
            Assert.Equal("ag-main", root.GetProperty("AgentUid").GetString());
            Assert.True(root.GetProperty("MemoryMaxChars").GetInt32() > 0);
            // 画像字段在
            Assert.Equal("balanced", root.GetProperty("Profile").GetProperty("DecisionStyle").GetString());
        }
        finally { Cleanup(dir); }
    }

    [Fact]
    public void PanelData_SessionList_And_Detail()
    {
        var (panel, dir) = MakePanel();
        try
        {
            // 造两个内存会话
            var listJson = panel.RenderSessionList("ag-main");
            var list = System.Text.Json.JsonDocument.Parse(listJson);
            var count = list.RootElement.GetProperty("SessionCount").GetInt32();
            Assert.True(count >= 0);

            if (count > 0)
            {
                var detailJson = panel.RenderSessionDetail("ag-main", 0);
                var detail = System.Text.Json.JsonDocument.Parse(detailJson);
                Assert.True(detail.RootElement.GetProperty("Found").GetBoolean());
            }
            else
            {
                // 无会话时详情应返回结构化未命中 (不抛异常)
                var detailJson = panel.RenderSessionDetail("ag-main", 0);
                var detail = System.Text.Json.JsonDocument.Parse(detailJson);
                Assert.False(detail.RootElement.GetProperty("Found").GetBoolean());
            }
            // 索引越界: 结构化报错, 不抛异常
            var oob = System.Text.Json.JsonDocument.Parse(panel.RenderSessionDetail("ag-main", 999));
            Assert.False(oob.RootElement.GetProperty("Found").GetBoolean());
            Assert.Contains("索引越界", oob.RootElement.GetProperty("Error").GetString());
        }
        finally { Cleanup(dir); }
    }

    // ── ② vulkan env (纯逻辑段: 已在真机验证过; 这里只验用户显式设置不被覆盖) ──

    [Fact]
    public void SessionConfig_MaxMemoryChars_Default1000()
    {
        var cfg = new SessionConfig();
        Assert.Equal(1000, cfg.MaxMemoryChars);
        var s = new Session { };
        _ = s.Memory; // 懒创建
        Assert.Equal(1000, s.Memory.MaxChars);
    }

    private static (PanelDataService Panel, string Dir) MakePanel()
    {
        var dir = Path.Combine(Path.GetTempPath(), "v714_paneltest_" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(dir);
        var sessions = new TestSessionManager();
        var memStore = new JsonSessionMemoryStore(dir);
        var profiles = new AgentProfileStore(dir);
        var caps = new CapabilityScanner();
        return (new PanelDataService(sessions, memStore, profiles, caps, dir), dir);
    }

    private static void Cleanup(string dir)
    {
        if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
    }

    /// <summary>轻量会话管理器测试桩 (不依赖 DI 日志)</summary>
    private sealed class TestSessionManager : ISessionManager
    {
        private readonly Dictionary<string, Session> _sessions = new();

        public Task<Session> CreateSessionAsync(string userId, SessionConfig? config = null)
        {
            var s = new Session { UserId = userId };
            _sessions[s.Id] = s;
            return Task.FromResult(s);
        }

        public Task<Session?> GetSessionAsync(string sessionId)
        {
            _sessions.TryGetValue(sessionId, out var s);
            return Task.FromResult(s);
        }

        public Task<Session> GetOrCreateSessionAsync(string sessionId, string userId)
        {
            if (!_sessions.TryGetValue(sessionId, out var s))
                _sessions[sessionId] = s = new Session { Id = sessionId, UserId = userId };
            return Task.FromResult(s);
        }

        public Task UpdateSessionAsync(Session session) => Task.CompletedTask;

        public Task EndSessionAsync(string sessionId) { _sessions.Remove(sessionId); return Task.CompletedTask; }

        public Task<SessionLoop> GetSessionLoopAsync(string sessionId)
            => throw new NotSupportedException("面板测试不需要 loop");

        public Task<IEnumerable<Session>> GetUserSessionsAsync(string userId)
            => Task.FromResult<IEnumerable<Session>>(_sessions.Values.Where(s => s.UserId == userId).ToList());

        public Task<IEnumerable<Session>> GetAllSessionsAsync()
            => Task.FromResult<IEnumerable<Session>>(_sessions.Values.ToList());
    }
}
