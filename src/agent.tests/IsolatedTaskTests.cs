using agent.intent;
using agent.session;
using agent.subagent;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 隔离任务测试 (plan_isolated_task.md I.5):
/// 无关判定规则、隔离边界 (独立会话/主记忆不污染)、结束即销毁、并发上限排队。
/// </summary>
public class IsolatedTaskTests
{
    // ── I.2 无关判定 ──

    [Fact]
    public void Calculator_Goal_Weather_Ask_Is_Isolated()
    {
        // 计算器开发中突然"查天气" → 实体零重叠 + 离题信号 → 隔离
        var (isIsolated, score, reason) = TaskRelevanceChecker.Check(
            new List<string> { "计算器", "表达式", "解析" },
            "开发计算器项目",
            "帮我查一下明天天气怎么样",
            "query",
            threshold: 2);
        Assert.True(isIsolated, $"score={score} reason={reason}");
    }

    [Fact]
    public void Calculator_Modify_Request_Is_Relevant()
    {
        // "把计算器改成十进制" → 实体重叠 (计算器) → 相关
        var (isIsolated, score, _) = TaskRelevanceChecker.Check(
            new List<string> { "计算器", "表达式", "解析" },
            "开发计算器项目",
            "把计算器改成十进制显示",
            "modify");
        Assert.False(isIsolated, $"score={score}");
    }

    [Fact]
    public void Deixis_Word_Vetoes_Isolation()
    {
        // 含指代词 "它" → 一票否决
        var (isIsolated, _, reason) = TaskRelevanceChecker.Check(
            new List<string> { "计算器" },
            "开发计算器项目",
            "把它删掉重写",
            "modify");
        Assert.False(isIsolated);
        Assert.Contains("指代词", reason);
    }

    // ── I.3/I.4 隔离执行与销毁 ──

    private sealed class FakeSessionManager : ISessionManager
    {
        public List<string> EndedSessions { get; } = new();
        public Task<Session> CreateSessionAsync(string userId, SessionConfig? config = null) =>
            Task.FromResult(new Session { Id = $"iso-{Guid.NewGuid():N}", UserId = userId });
        public Task EndSessionAsync(string sessionId)
        {
            EndedSessions.Add(sessionId);
            return Task.CompletedTask;
        }
        // 未用接口成员 (隔离器只用 Create/End):
        public Task<Session?> GetSessionAsync(string sessionId) => Task.FromResult<Session?>(null);
        public Task<Session> GetOrCreateSessionAsync(string sessionId, string userId) =>
            Task.FromResult(new Session { Id = sessionId, UserId = userId });
        public Task UpdateSessionAsync(Session session) => Task.CompletedTask;
        public Task<SessionLoop> GetSessionLoopAsync(string sessionId) =>
            throw new NotImplementedException("隔离测试不需要会话循环");
        public Task<IEnumerable<Session>> GetUserSessionsAsync(string userId) =>
            Task.FromResult<IEnumerable<Session>>(Array.Empty<Session>());
        public Task<IEnumerable<Session>> GetAllSessionsAsync() =>
            Task.FromResult<IEnumerable<Session>>(Array.Empty<Session>());
    }

    private sealed class StubIsolatedLlm : ILLMCallerForIsolated
    {
        public int Calls { get; private set; }
        public Task<LLMResponse> CallAsync(agent.templates.Prompt prompt, CancellationToken ct = default)
        {
            Calls++;
            Assert.Contains("一次性隔离子任务执行器", prompt.SystemPrompt);
            return Task.FromResult(new LLMResponse { Content = "晴, 25°C", Success = true });
        }
    }

    [Fact]
    public async Task Execute_Creates_Independent_Session_And_Destroys_After()
    {
        var sessions = new FakeSessionManager();
        var llm = new StubIsolatedLlm();
        var runner = new IsolatedTaskRunner(sessions, llm, NullLogger.Instance);
        var result = await runner.ExecuteAsync("查明天天气", "2:实体零重叠");

        Assert.True(result.Success);
        Assert.Equal("晴, 25°C", result.Answer);
        Assert.StartsWith("iso-", result.IsolatedSessionId);
        // 销毁边界: 会话 End 被调用 (结束即销毁)
        Assert.Single(sessions.EndedSessions);
        Assert.Equal(result.IsolatedSessionId, sessions.EndedSessions[0]);
    }

    [Fact]
    public async Task Concurrency_Cap_Two_Third_Waits()
    {
        var sessions = new FakeSessionManager();
        var gate = new TaskCompletionSource();
        var runner = new IsolatedTaskRunner(sessions, new GatedLlm(gate), NullLogger.Instance, maxConcurrent: 2);

        var t1 = runner.ExecuteAsync("任务1", "x");
        var t2 = runner.ExecuteAsync("任务2", "x");
        var t3 = runner.ExecuteAsync("任务3", "x");

        await Task.Delay(80);
        Assert.False(t3.IsCompleted, "第 3 个应排队 (上限 2)");
        gate.SetResult();
        await Task.WhenAll(t1, t2, t3);
    }

    private sealed class GatedLlm(TaskCompletionSource gate) : ILLMCallerForIsolated
    {
        public async Task<LLMResponse> CallAsync(agent.templates.Prompt prompt, CancellationToken ct = default)
        {
            await gate.Task;
            return new LLMResponse { Content = "ok", Success = true };
        }
    }
}
