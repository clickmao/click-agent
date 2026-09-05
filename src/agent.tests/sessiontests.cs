using Xunit;
using Microsoft.Extensions.Logging;
using agent.session;
using agent.core;

namespace agent.tests;

/// <summary>
/// SessionManager / Session 单元测试（针对真实实现）
/// </summary>
public class SessionTests
{
    private static SessionManager CreateManager()
    {
        var loggerFactory = LoggerFactory.Create(b => b.SetMinimumLevel(LogLevel.Critical));
        return new SessionManager(loggerFactory.CreateLogger<SessionManager>());
    }

    [Fact]
    public async Task CreateSessionAsync_ShouldReturnNewSession()
    {
        // Arrange
        var manager = CreateManager();
        var userId = "user-123";

        // Act
        var session = await manager.CreateSessionAsync(userId);

        // Assert
        Assert.NotNull(session);
        Assert.Equal(userId, session.UserId);
        Assert.False(string.IsNullOrEmpty(session.Id));
        Assert.Equal(SessionState.Active, session.State);
        Assert.Empty(session.Messages);
    }

    [Fact]
    public async Task CreateSessionAsync_ShouldAssignUniqueIds()
    {
        // Arrange
        var manager = CreateManager();

        // Act
        var s1 = await manager.CreateSessionAsync("user-A");
        var s2 = await manager.CreateSessionAsync("user-B");

        // Assert
        Assert.NotEqual(s1.Id, s2.Id);
    }

    [Fact]
    public async Task GetSessionAsync_ShouldReturnExistingSession()
    {
        // Arrange
        var manager = CreateManager();
        var created = await manager.CreateSessionAsync("user-123");

        // Act
        var fetched = await manager.GetSessionAsync(created.Id);

        // Assert
        Assert.NotNull(fetched);
        Assert.Equal(created.Id, fetched!.Id);
        Assert.Equal("user-123", fetched.UserId);
    }

    [Fact]
    public async Task GetSessionAsync_UnknownId_ShouldReturnNull()
    {
        // Arrange
        var manager = CreateManager();

        // Act
        var fetched = await manager.GetSessionAsync("nonexistent-session-id");

        // Assert
        Assert.Null(fetched);
    }

    [Fact]
    public async Task UpdateSessionAsync_ShouldPersistChanges()
    {
        // Arrange
        var manager = CreateManager();
        var session = await manager.CreateSessionAsync("user-123");
        session.AddUserMessage("你好");
        session.AddAssistantMessage("你好！有什么可以帮你？");

        // Act
        await manager.UpdateSessionAsync(session);
        var fetched = await manager.GetSessionAsync(session.Id);

        // Assert
        Assert.NotNull(fetched);
        Assert.Equal(2, fetched!.Messages.Count);
        Assert.Equal(1, fetched.TurnCount); // 只有 AddUserMessage 递增 TurnCount
    }

    [Fact]
    public async Task EndSessionAsync_ShouldReleaseSessionFromMemory()
    {
        // Arrange
        var manager = CreateManager();
        var session = await manager.CreateSessionAsync("user-123");

        // Act
        await manager.EndSessionAsync(session.Id);
        var fetched = await manager.GetSessionAsync(session.Id);

        // Assert (v7.8: End 即释放 — Completed 会话留字典 = 内存泄漏; 二次 End 幂等)
        Assert.Null(fetched);
        var ex = await Record.ExceptionAsync(() => manager.EndSessionAsync(session.Id));
        Assert.Null(ex);
    }

    [Fact]
    public void AddUserMessage_ShouldRecordMessage()
    {
        // Arrange
        var session = new Session { UserId = "user-123" };

        // Act
        session.AddUserMessage("测试消息");

        // Assert
        Assert.Single(session.Messages);
        Assert.Equal("测试消息", session.Messages[0].Content);
        Assert.Equal(MessageRole.User, session.Messages[0].Role);
    }

    [Fact]
    public void AddAssistantMessage_ShouldRecordMessage()
    {
        // Arrange
        var session = new Session { UserId = "user-123" };

        // Act
        session.AddAssistantMessage("助手回复");

        // Assert
        Assert.Single(session.Messages);
        Assert.Equal("助手回复", session.Messages[0].Content);
    }

    [Fact]
    public void GetRecentMessages_ShouldReturnLastNMessages()
    {
        // Arrange
        var session = new Session { UserId = "user-123" };
        for (int i = 0; i < 10; i++)
        {
            session.AddUserMessage($"消息 {i}");
        }

        // Act
        var recent = session.GetRecentMessages(3);

        // Assert
        Assert.Equal(3, recent.Count);
        Assert.Equal("消息 7", recent[0].Content);
        Assert.Equal("消息 9", recent[2].Content);
    }

    [Fact]
    public void GetRelevantMessages_ShouldReturnMatchingMessages()
    {
        // Arrange
        var session = new Session { UserId = "user-123" };
        session.AddUserMessage("帮我写一个解析器");
        session.AddUserMessage("今天天气怎么样");
        session.AddUserMessage("解析器要用C#写");

        // Act
        var relevant = session.GetRelevantMessages("解析器", 5);

        // Assert
        Assert.Equal(2, relevant.Count);
        Assert.All(relevant, m => Assert.Contains("解析器", m.Content));
    }

    [Fact]
    public void GetConversationSummary_ShouldRespectMaxLength()
    {
        // Arrange
        var session = new Session { UserId = "user-123" };
        session.AddUserMessage(new string('a', 500));
        session.AddAssistantMessage(new string('b', 500));

        // Act
        var summary = session.GetConversationSummary(100);

        // Assert - 实现: 截断到 maxLength 再加 "..."，总长 = maxLength + 3
        Assert.True(summary.Length <= 103);
        Assert.EndsWith("...", summary);
    }
}
