using agent.session;
using Xunit;

namespace agent.tests;

/// <summary>
/// R370 · L2-F1 跨会话检索 (SessionHistorySearch) 单测。
/// 铁律: 每项能力都要有**真断言** (不是"跑通即通过"), 且必须有负向控制。
/// </summary>
public sealed class SessionHistorySearchTests : IDisposable
{
    private readonly string _dir;
    private readonly JsonSessionMemoryStore _store;

    public SessionHistorySearchTests()
    {
        _dir = Path.Combine(Path.GetTempPath(), "af-session-search-" + Guid.NewGuid().ToString("N")[..8]);
        _store = new JsonSessionMemoryStore(_dir);
    }

    public void Dispose()
    {
        try
        {
            if (Directory.Exists(_dir))
                Directory.Delete(_dir, recursive: true);
        }
        catch
        { /* 清理失败不影响断言 */
        }
    }

    private void Seed(string sessionId, string note, string? goal = null)
    {
        var mem = new SessionMemory();
        if (goal != null)
            mem.SetGoal(goal);
        mem.Remember(note);
        _store.Save(sessionId, mem);
    }

    private SessionHistorySearch NewSearch() => new(new SessionHistorySearch.StoreSource(_store));

    [Fact]
    public void Search_Ranks_Session_Containing_Unique_Term_First()
    {
        Seed("s-vector", "实现了 向量召回 与 嵌入缓存 两层", goal: "提升召回质量");
        Seed("s-frontend", "前端事件信封 与 通知通路 接线", goal: "前端联调");

        var hits = NewSearch().Search("向量召回 嵌入", topK: 5);

        Assert.NotEmpty(hits);
        Assert.Equal("s-vector", hits[0].SessionId);
        Assert.DoesNotContain(hits, h => h.SessionId == "s-frontend");
        Assert.True(hits[0].Score > 0);
    }

    [Fact]
    public void Search_Is_Deterministic_Across_Calls()
    {
        Seed("s-a", "教训表 归 role 模块 含提交 API");
        Seed("s-b", "教训表 与 记忆 注入 链路");
        Seed("s-c", "无关内容 像素 渲染");

        var search = NewSearch();
        var r1 = search.Search("教训表 提交 API", topK: 3);
        var r2 = search.Search("教训表 提交 API", topK: 3);

        Assert.Equal(r1.Count, r2.Count);
        for (var i = 0; i < r1.Count; i++)
        {
            Assert.Equal(r1[i].SessionId, r2[i].SessionId);
            Assert.Equal(r1[i].Score, r2[i].Score);
        }
    }

    [Fact]
    public void Empty_Or_Blank_Query_Returns_Empty()
    {
        Seed("s-a", "任意内容");
        var search = NewSearch();
        Assert.Empty(search.Search(""));
        Assert.Empty(search.Search("   "));
        Assert.Empty(search.Search("任意内容", topK: 0));
    }

    [Fact]
    public void Unrelated_Query_Returns_Empty_NegativeControl()
    {
        Seed("s-a", "向量召回 与 嵌入缓存");
        var hits = NewSearch().Search("完全不相干的外星词根zzq", topK: 5);
        Assert.Empty(hits);
    }

    [Fact]
    public void TopK_Is_Respected()
    {
        Seed("s-1", "共享标记 甲");
        Seed("s-2", "共享标记 乙");
        Seed("s-3", "共享标记 丙");
        var hits = NewSearch().Search("共享标记", topK: 2);
        Assert.Equal(2, hits.Count);
    }

    [Fact]
    public void Snippet_Is_Bounded_And_Contains_Matched_Text()
    {
        Seed("s-long", new string('前', 300) + " 关键锚点 向量重排 " + new string('后', 300));
        var hits = NewSearch().Search("向量重排", topK: 1);
        Assert.Single(hits);
        Assert.True(hits[0].Snippet.Length <= 124, $"片段长度越界: {hits[0].Snippet.Length}");
        Assert.Contains("向量重排", hits[0].Snippet);
    }

    [Fact]
    public void Idf_Downscores_Term_Shared_By_All_Sessions()
    {
        Seed("s-a", "共享词 加上 特有词甲");
        Seed("s-b", "共享词 加上 其它内容");

        var search = NewSearch();
        var unique = search.Search("特有词甲", topK: 5);
        var common = search.Search("共享词", topK: 5);

        Assert.NotEmpty(unique);
        Assert.NotEmpty(common);
        double ScoreOf(IReadOnlyList<SessionHistorySearch.Hit> hs, string id)
            => hs.Single(h => h.SessionId == id).Score;

        Assert.True(ScoreOf(unique, "s-a") > ScoreOf(common, "s-a"),
            "独有词的 IDF 权重必须高于广布词 (否则判别力退化为纯词频)");
    }

    [Fact]
    public void Search_Does_Not_Write_Any_File_ReadOnly_Guarantee()
    {
        Seed("s-a", "只读性 验证 标记");
        var sessionsDir = Path.Combine(_dir, "sessions");
        var before = Directory.GetFiles(sessionsDir).OrderBy(f => f, StringComparer.Ordinal).ToArray();
        var beforeWriteTime = before.Select(File.GetLastWriteTimeUtc).ToArray();

        var hits = NewSearch().Search("只读性 验证", topK: 5);
        Assert.NotEmpty(hits);

        var after = Directory.GetFiles(sessionsDir).OrderBy(f => f, StringComparer.Ordinal).ToArray();
        Assert.Equal(before.Length, after.Length);
        for (var i = 0; i < after.Length; i++)
            Assert.Equal(beforeWriteTime[i], File.GetLastWriteTimeUtc(after[i]));
    }

    [Fact]
    public void Document_Builder_Includes_Goal_And_Constraints()
    {
        var mem = new SessionMemory();
        mem.SetGoal("目标句: 提升召回", keyEntities: new[] { "bge-small" }, constraints: new[] { "AOT 0 IL" });
        mem.AddMilestone("评测台落地");

        var doc = SessionHistorySearch.BuildDocument(mem);

        Assert.Contains("提升召回", doc);
        Assert.Contains("bge-small", doc);
        Assert.Contains("AOT 0 IL", doc);
        Assert.Contains("评测台落地", doc);
    }

    [Fact]
    public void Missing_Session_File_Is_Skipped_Not_Thrown()
    {
        Seed("s-real", "真实会话 内容 检索");
        var search = NewSearch();
        // 枚举里混入不存在的 id (模拟并发删除/半截文件)
        var hits = new SessionHistorySearch(
            new MixedSource(new SessionHistorySearch.StoreSource(_store), "s-ghost")).Search("真实会话", topK: 5);
        Assert.Single(hits);
        Assert.Equal("s-real", hits[0].SessionId);
    }

    private sealed class MixedSource : SessionHistorySearch.ISource
    {
        private readonly SessionHistorySearch.ISource _inner;
        private readonly string _ghost;
        public MixedSource(SessionHistorySearch.ISource inner, string ghost) { _inner = inner; _ghost = ghost; }
        public IReadOnlyList<string> EnumerateSessionIds()
        {
            var ids = new List<string>(_inner.EnumerateSessionIds()) { _ghost };
            return ids;
        }
        public SessionMemory? Load(string sessionId) => _inner.Load(sessionId);
    }
}
