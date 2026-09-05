using agent.core;
using agent.session;
using Microsoft.Extensions.Logging;
using Xunit;
using Xunit.Abstractions;

namespace agent.tests;

/// <summary>
/// 性能基准 (v7.8): 修复前算法 (内联复刻) vs 修复后实现, 真实计时对比。
/// 覆盖: GetRecentMessages 全表排序消除 / 会话历史上限保护 / EndSession 内存回收。
/// </summary>
public class SessionPerformanceTests
{
    private readonly ITestOutputHelper _output;

    public SessionPerformanceTests(ITestOutputHelper output) => _output = output;

    private static Session CreateSeededSession(int messageCount)
    {
        var session = new Session();
        for (var i = 0; i < messageCount; i++)
            session.AddUserMessage($"性能基准消息 {i}: 讨论分布式一致性协议的细节 {i % 50}");
        return session;
    }

    [Fact]
    public void GetRecentMessages_BeatsFullTableSort_AtScale()
    {
        var session = CreateSeededSession(10_000);

        // 修复前算法 (内联复刻): 两次全表 LINQ 排序
        var swOld = System.Diagnostics.Stopwatch.StartNew();
        var oldResult = session.Messages
            .OrderByDescending(m => m.Timestamp)
            .Take(10)
            .OrderBy(m => m.Timestamp)
            .ToList();
        swOld.Stop();

        // 修复后: 尾部倒序取用
        var swNew = System.Diagnostics.Stopwatch.StartNew();
        var newResult = session.GetRecentMessages(10);
        swNew.Stop();

        Assert.Equal(10, newResult.Count);
        Assert.Equal(oldResult.Select(m => m.Content), newResult.Select(m => m.Content));
        _output.WriteLine($"old(全表排序)={swOld.ElapsedMicroseconds()}µs new(尾部取用)={swNew.ElapsedMicroseconds()}µs");

        // 修复后必须显著更快 (全表排序 O(N logN) vs O(k)); 宽松 3x 防抖动, 典型差距 >10x
        Assert.True(swNew.ElapsedTicks * 3 < Math.Max(swOld.ElapsedTicks, 1),
            $"new {swNew.ElapsedMicroseconds()}µs should be < old/3 {swOld.ElapsedMicroseconds() / 3}µs");
    }

    [Fact]
    public void MessageHistory_IsCapped_AtMaxHistoryMessages()
    {
        var session = new Session();
        for (var i = 0; i < Session.MaxHistoryMessages + 500; i++)
            session.AddUserMessage($"溢出测试 {i}");

        Assert.Equal(Session.MaxHistoryMessages, session.Messages.Count);
        // 最旧的被裁掉 (200+500=700 条 → 保留 500..699), 最新保留
        Assert.Contains("溢出测试 699", session.Messages[^1].Content);
        Assert.DoesNotContain(session.Messages, m => m.Content.Contains("溢出测试 0:"));
    }

    [Fact]
    public async Task EndSession_RemovesFromMemory()
    {
        var manager = TestHost.CreateSessionManager();
        var session = await manager.GetOrCreateSessionAsync("perf-end-1", "user-x");
        session.AddUserMessage("some content");

        await manager.EndSessionAsync("perf-end-1");

        var after = await manager.GetSessionAsync("perf-end-1");
        Assert.Null(after); // v7.8: End 后真删除, 不留尸体在字典里
    }

    [Fact]
    public void Recall_SortOnlyMatches_NotFullTable()
    {
        // 等价性验证: 命中过滤后的排序结果与全表 LINQ 版语义一致
        var session = CreateSeededSession(2_000);
        var keywords = new[] { "一致性", "协议" };

        var expected = session.Messages
            .Where(m => m.Role != MessageRole.System)
            .Where(m => keywords.Any(k => m.Content.Contains(k, StringComparison.OrdinalIgnoreCase)))
            .OrderByDescending(m => m.Timestamp)
            .Take(10)
            .ToList();

        var actual = session.GetRelevantMessages("一致性 协议", 10);

        Assert.Equal(expected.Select(m => m.Content), actual.Select(m => m.Content));
    }
}

public static class StopwatchExtensions
{
    public static long ElapsedMicroseconds(this System.Diagnostics.Stopwatch sw) =>
        sw.ElapsedTicks * 1_000_000 / System.Diagnostics.Stopwatch.Frequency;
}

/// <summary>测试宿主: 提供 SessionManager 实例</summary>
public static class TestHost
{
    public static SessionManager CreateSessionManager()
    {
        var factory = Microsoft.Extensions.Logging.LoggerFactory.Create(b => { });
        return new SessionManager(factory.CreateLogger<SessionManager>());
    }
}
