using agent.session;
using Microsoft.Extensions.Logging;
using Xunit;

namespace agent.tests;

/// <summary>
/// SessionManager 契约测试: GetOrCreateSessionAsync 幂等性与指定 Id 语义。
/// 背景: V2 曾因 GetSessionAsync 返回 null 而静默丢弃多轮对话历史 (v7.5 修复)。
/// </summary>
public class SessionManagerTests
{
    private static SessionManager Create()
    {
        var factory = Microsoft.Extensions.Logging.LoggerFactory.Create(b => { });
        return new SessionManager(factory.CreateLogger<SessionManager>());
    }

    [Fact]
    public async Task GetOrCreateSessionAsync_CreatesWithCallerSpecifiedId()
    {
        var manager = Create();

        var session = await manager.GetOrCreateSessionAsync("msg-session-1", "user-a");

        Assert.Equal("msg-session-1", session.Id);
        Assert.Equal("user-a", session.UserId);
        Assert.Equal(agent.core.SessionState.Active, session.State);
    }

    [Fact]
    public async Task GetOrCreateSessionAsync_IsIdempotent()
    {
        var manager = Create();

        var first = await manager.GetOrCreateSessionAsync("msg-session-2", "user-a");
        first.AddUserMessage("turn one");
        await manager.UpdateSessionAsync(first);

        var second = await manager.GetOrCreateSessionAsync("msg-session-2", "user-a");

        // 同一会话 (非新建): 历史保留 — 多轮对话记忆的前提
        Assert.Same(first, second);
        Assert.Contains(second.Messages, m => m.Content == "turn one");
    }

    [Fact]
    public async Task GetSessionAsync_ReturnsNull_WhenNeverCreated()
    {
        var manager = Create();

        var missing = await manager.GetSessionAsync("never-created");

        Assert.Null(missing);
    }
}
