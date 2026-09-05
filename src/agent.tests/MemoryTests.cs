using Xunit;
using Moq;
using Microsoft.Extensions.Logging;
using agent.memory;
using agent.core;

namespace agent.tests;

/// <summary>
/// IMemoryStore / MemoryStore 单元测试（针对真实实现）
/// </summary>
public class MemoryTests
{
    private static MemoryStore CreateStore()
    {
        var loggerFactory = LoggerFactory.Create(b => b.SetMinimumLevel(LogLevel.Critical));
        return new MemoryStore(loggerFactory.CreateLogger<MemoryStore>());
    }

    [Fact]
    public async Task StoreAsync_ShouldReturnEntryId()
    {
        // Arrange
        var store = CreateStore();
        var entry = new MemoryEntry
        {
            Content = "测试记忆内容",
            MemoryType = MemoryType.ShortTerm
        };

        // Act
        var id = await store.StoreAsync(entry);

        // Assert
        Assert.False(string.IsNullOrEmpty(id));
    }

    [Fact]
    public async Task GetAsync_ShouldReturnStoredEntry()
    {
        // Arrange
        var store = CreateStore();
        var entry = new MemoryEntry { Content = "可检索的记忆", MemoryType = MemoryType.LongTerm };
        var id = await store.StoreAsync(entry);

        // Act
        var fetched = await store.GetAsync(id);

        // Assert
        Assert.NotNull(fetched);
        Assert.Equal("可检索的记忆", fetched!.Content);
        Assert.Equal(MemoryType.LongTerm, fetched.MemoryType);
    }

    [Fact]
    public async Task GetAsync_UnknownId_ShouldReturnNull()
    {
        // Arrange
        var store = CreateStore();

        // Act
        var fetched = await store.GetAsync("nonexistent-id");

        // Assert
        Assert.Null(fetched);
    }

    [Fact]
    public async Task SearchAsync_ShouldReturnMatchingEntries()
    {
        // Arrange
        var store = CreateStore();
        await store.StoreAsync(new MemoryEntry { Content = "解析器设计讨论", MemoryType = MemoryType.LongTerm });
        await store.StoreAsync(new MemoryEntry { Content = "天气很好的日子", MemoryType = MemoryType.ShortTerm });
        await store.StoreAsync(new MemoryEntry { Content = "解析器性能优化", MemoryType = MemoryType.LongTerm });

        // Act
        var results = await store.SearchAsync("解析器");

        // Assert
        Assert.Equal(2, results.Count);
        Assert.All(results, e => Assert.Contains("解析器", e.Content));
    }

    [Fact]
    public async Task UpdateAsync_ShouldModifyEntry()
    {
        // Arrange
        var store = CreateStore();
        var entry = new MemoryEntry { Content = "原始内容", MemoryType = MemoryType.ShortTerm };
        var id = await store.StoreAsync(entry);

        var updated = await store.GetAsync(id);
        Assert.NotNull(updated);
        updated!.Importance = 9.5;

        // Act
        await store.UpdateAsync(updated);
        var fetched = await store.GetAsync(id);

        // Assert
        Assert.NotNull(fetched);
        Assert.Equal(9.5, fetched!.Importance);
    }

    [Fact]
    public async Task DeleteAsync_ShouldRemoveEntry()
    {
        // Arrange
        var store = CreateStore();
        var id = await store.StoreAsync(new MemoryEntry { Content = "将被删除" });

        // Act
        await store.DeleteAsync(id);
        var fetched = await store.GetAsync(id);

        // Assert
        Assert.Null(fetched);
    }

    [Fact]
    public async Task GetRecentAsync_ShouldReturnLimitedCount()
    {
        // Arrange
        var store = CreateStore();
        for (int i = 0; i < 15; i++)
        {
            await store.StoreAsync(new MemoryEntry { Content = $"记忆条目 {i}" });
        }

        // Act
        var recent = await store.GetRecentAsync(5);

        // Assert
        Assert.Equal(5, recent.Count);
    }

    [Fact]
    public async Task ClearSessionAsync_ShouldOnlyClearSessionEntries()
    {
        // Arrange
        var store = CreateStore();
        await store.StoreAsync(new MemoryEntry { Content = "会话A记忆", SessionId = "session-A" });
        await store.StoreAsync(new MemoryEntry { Content = "会话B记忆", SessionId = "session-B" });

        // Act
        await store.ClearSessionAsync("session-A");
        var remainingA = await store.GetBySessionAsync("session-A");
        var remainingB = await store.GetBySessionAsync("session-B");

        // Assert
        Assert.Empty(remainingA);
        Assert.Single(remainingB);
    }

    [Fact]
    public async Task GetStatisticsAsync_ShouldReportCounts()
    {
        // Arrange
        var store = CreateStore();
        await store.StoreAsync(new MemoryEntry { Content = "短期1", MemoryType = MemoryType.ShortTerm });
        await store.StoreAsync(new MemoryEntry { Content = "长期1", MemoryType = MemoryType.LongTerm });
        await store.StoreAsync(new MemoryEntry { Content = "长期2", MemoryType = MemoryType.LongTerm });

        // Act
        var stats = await store.GetStatisticsAsync();

        // Assert
        Assert.Equal(3, stats.TotalEntries);
        Assert.Equal(1, stats.ShortTermCount);
        Assert.Equal(2, stats.LongTermCount);
    }
}
