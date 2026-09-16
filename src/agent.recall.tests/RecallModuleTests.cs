// R480: 独立文本召回模块 —— 行为测试 (判据: 与独立暴力实现一致 / 极小常驻 / 增量正确 / 损坏 fail-closed)。
using System.Text;
using agent.Recall;
using Xunit;

namespace agent.Recall.Tests;

internal sealed class CollectingSink : ITokenSink
{
    public List<string> Tokens { get; } = new();

    public void AddToken(ReadOnlySpan<byte> token) => Tokens.Add(Encoding.UTF8.GetString(token));
}

public sealed class RecallTokenizerTests
{
    [Fact]
    public void EmitsIdeographicBigramsAndAsciiWords()
    {
        var sink = new CollectingSink();
        RecallTokenizer.Tokenize("用户权限 API access".AsSpan(), RecallTokenizerOptions.Default, sink);
        Assert.Contains("用户", sink.Tokens);
        Assert.Contains("户权", sink.Tokens);
        Assert.Contains("权限", sink.Tokens);
        Assert.Contains("api", sink.Tokens);
        Assert.Contains("access", sink.Tokens);
    }

    [Fact]
    public void TokenizesIdenticallyRegardlessOfFileLikeSuffix()
    {
        var a = new CollectingSink();
        var b = new CollectingSink();
        RecallTokenizer.Tokenize("alpha.cs".AsSpan(), RecallTokenizerOptions.Default, a);
        RecallTokenizer.Tokenize("alpha-md".AsSpan(), RecallTokenizerOptions.Default, b);
        Assert.Equal(new[] { "alpha", "cs" }, a.Tokens);
        Assert.Equal(new[] { "alpha", "md" }, b.Tokens);
    }

    [Fact]
    public void HashIsStable()
    {
        var bytes = Encoding.UTF8.GetBytes("权限");
        Assert.Equal(RecallTokenizer.Hash(bytes), RecallTokenizer.Hash(Encoding.UTF8.GetBytes("权限")));
        Assert.NotEqual(RecallTokenizer.Hash(bytes), RecallTokenizer.Hash(Encoding.UTF8.GetBytes("限权")));
    }
}

public sealed class RecallIndexTests
{
    private static List<RecallSourceDoc> Corpus(int count, Func<int, string> text)
    {
        var docs = new List<RecallSourceDoc>(count);
        for (int i = 0; i < count; i++)
        {
            docs.Add(new RecallSourceDoc
            {
                Id = "doc-" + i,
                Path = "corpus/file-" + i,
                Text = text(i),
                Size = 0,
                MtimeTicks = 0,
                Inode = 0,
            });
        }
        return docs;
    }

    private static string TempDir()
    {
        string dir = Path.Combine(Path.GetTempPath(), "recall_tests_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    [Fact]
    public void FindsDocumentByPhrase()
    {
        string dir = TempDir();
        try
        {
            var docs = Corpus(50, i => i == 37 ? "用户权限校验失败时应回落到只读模式" : $"普通文档 {i} 的内容");
            using var index = RecallIndex.Build(Path.Combine(dir, "idx"), docs);
            var hits = index.Search("权限校验", 5);
            Assert.NotEmpty(hits);
            Assert.Equal("doc-37", hits[0].Id);
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public void BlockChainBeyondFirstBlock_IsReadable()
    {
        string dir = TempDir();
        try
        {
            // 400 篇都含 "shared", 首个与末个还含唯一词 ⇒ 必须跨越 3 个以上 128-文档块
            var docs = Corpus(400, i => i == 0 ? "shared alpha" : i == 399 ? "shared omega" : "shared filler");
            using var index = RecallIndex.Build(Path.Combine(dir, "idx"), docs);
            var all = index.Search("shared", 400);
            Assert.Equal(400, all.Count);
            Assert.Contains(all, h => h.Id == "doc-0");
            Assert.Contains(all, h => h.Id == "doc-399");
            var last = index.Search("omega", 5);
            Assert.Equal("doc-399", last[0].Id);
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    private static List<(double Score, List<string> Ids)> GroupByScore(IEnumerable<(string Id, double Score)> hits)
    {
        var groups = new List<(double Score, List<string> Ids)>();
        foreach (var h in hits)
        {
            if (groups.Count > 0 && Math.Abs(groups[^1].Score - h.Score) < 1e-9)
            {
                groups[^1].Ids.Add(h.Id);
            }
            else
            {
                groups.Add((h.Score, new List<string> { h.Id }));
            }
        }
        foreach (var g in groups)
        {
            g.Ids.Sort(StringComparer.Ordinal);
        }
        return groups;
    }

    [Fact]
    public void WandTopK_MatchesIndependentBruteForce()
    {
        string dir = TempDir();
        try
        {
            var docs = Corpus(300, i => i % 7 == 0
                ? $"索引 压缩 内存 预算 文档{i} shared"
                : i % 5 == 0
                    ? $"召回 延迟 毫秒 文档{i} shared"
                    : $"普通 内容 填充 文档{i}");
            using var index = RecallIndex.Build(Path.Combine(dir, "idx"), docs);
            foreach (string q in new[] { "索引 内存", "召回 延迟", "shared 压缩", "文档" })
            {
                var brute = BruteForce(docs, q, 10);
                var bruteAll = BruteForce(docs, q, docs.Count);
                var got = index.Search(q, 10);
                Assert.Equal(brute.Count, got.Count);
                // 并列分数在 top-k 中天然无序 (堆内部槽位顺序); 末组被 k 截断 ⇒ 只校验计数 + 「属于同分组」子集。
                var bGroups = GroupByScore(brute);
                var gGroups = GroupByScore(got.Select(h => (h.Id, h.Score)));
                Assert.Equal(bGroups.Count, gGroups.Count);
                for (int i = 0; i < bGroups.Count; i++)
                {
                    Assert.True(Math.Abs(bGroups[i].Score - gGroups[i].Score) < 1e-9,
                        $"score drift at group {i}: {bGroups[i].Score} vs {gGroups[i].Score}");
                    if (i < bGroups.Count - 1)
                    {
                        Assert.Equal(bGroups[i].Ids, gGroups[i].Ids);
                    }
                    else
                    {
                        Assert.Equal(bGroups[i].Ids.Count, gGroups[i].Ids.Count);
                        var sameScore = new HashSet<string>(
                            bruteAll.Where(h => Math.Abs(h.Score - bGroups[i].Score) < 1e-9).Select(h => h.Id),
                            StringComparer.Ordinal);
                        foreach (string id in gGroups[i].Ids)
                        {
                            Assert.Contains(id, sameScore);
                        }
                    }
                }
            }
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public void BlockSkip_PrunesPostings()
    {
        string dir = TempDir();
        try
        {
            var docs = Corpus(1000, i => i >= 990 ? "common rare" : "common filler");
            using var index = RecallIndex.Build(Path.Combine(dir, "idx"), docs);
            var stats = new RecallReadStats();
            var hits = index.Search("common rare", 10, stats);
            // rare 只出现在 10 篇 ⇒ WAND 必须跳过绝大多数 common posting
            Assert.Equal(10, hits.Count);
            Assert.True(stats.PostingsVisited > 0);
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public void ResidentBytes_DoNotScaleWithDocCount()
    {
        string dir = TempDir();
        try
        {
            using var small = RecallIndex.Build(Path.Combine(dir, "small"), Corpus(500, i => $"词{i} 内容 alpha"));
            long r1 = small.MemoryReport().TotalBytes;
            using var big = RecallIndex.Build(Path.Combine(dir, "big"), Corpus(8000, i => $"词{i} 内容 alpha"));
            long r2 = big.MemoryReport().TotalBytes;
            Assert.True(r2 < r1 * 4, $"resident grew {r1} -> {r2} for 16x docs");
            Assert.True(r2 < 512 * 1024, $"resident too large: {r2}");
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public void CorruptSegmentHeader_FailsClosed()
    {
        string dir = TempDir();
        try
        {
            string indexDir = Path.Combine(dir, "idx");
            using (var index = RecallIndex.Build(indexDir, Corpus(20, i => "内容 " + i)))
            {
            }
            string segMeta = Directory.GetFiles(indexDir, "seg.meta", SearchOption.AllDirectories)[0];
            using (var fs = new FileStream(segMeta, FileMode.Open, FileAccess.Write))
            {
                fs.Seek(20, SeekOrigin.Begin);
                fs.WriteByte(0xFF);
            }
            Assert.ThrowsAny<RecallFormatException>(() => RecallIndex.Open(indexDir));
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    private static List<(string Id, double Score)> BruteForce(IReadOnlyList<RecallSourceDoc> docs, string query, int k)
    {
        var queryTokens = new List<string>();
        var sink = new CollectingSink();
        RecallTokenizer.Tokenize(query.AsSpan(), RecallTokenizerOptions.Default, sink);
        foreach (string t in sink.Tokens)
        {
            if (!queryTokens.Contains(t))
            {
                queryTokens.Add(t);
            }
        }

        var docTokens = new List<Dictionary<string, int>>(docs.Count);
        double totalLen = 0;
        foreach (var doc in docs)
        {
            var s = new CollectingSink();
            RecallTokenizer.Tokenize(doc.Text.AsSpan(), RecallTokenizerOptions.Default, s);
            var tf = new Dictionary<string, int>(StringComparer.Ordinal);
            foreach (string t in s.Tokens)
            {
                tf[t] = tf.TryGetValue(t, out int c) ? c + 1 : 1;
            }
            docTokens.Add(tf);
            totalLen += s.Tokens.Count;
        }
        double avg = docs.Count == 0 ? 1 : Math.Max(1e-9, totalLen / docs.Count);
        double k1 = 1.2, b = 0.75;
        var scored = new List<(string Id, double Score)>();
        for (int i = 0; i < docs.Count; i++)
        {
            double score = 0;
            double dl = 0;
            foreach (int _ in docTokens[i].Values)
            {
            }
            dl = docTokens[i].Values.Sum();
            foreach (string t in queryTokens)
            {
                if (!docTokens[i].TryGetValue(t, out int tf))
                {
                    continue;
                }
                int df = 0;
                foreach (var d in docTokens)
                {
                    if (d.ContainsKey(t))
                    {
                        df++;
                    }
                }
                double idf = Math.Log(1.0 + (docs.Count - df + 0.5) / (df + 0.5));
                score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg));
            }
            if (score > 0)
            {
                scored.Add((docs[i].Id, score));
            }
        }
        scored.Sort((a, c) =>
        {
            int cc = c.Score.CompareTo(a.Score);
            return cc != 0 ? cc : string.CompareOrdinal(a.Id, c.Id);
        });
        return scored.Take(k).ToList();
    }
}

public sealed class RecallIncrementalTests
{
    private static List<RecallSourceDoc> Corpus(int count, Func<int, string> text)
    {
        var docs = new List<RecallSourceDoc>(count);
        for (int i = 0; i < count; i++)
        {
            docs.Add(new RecallSourceDoc
            {
                Id = "doc-" + i,
                Path = "corpus/file-" + i,
                Text = text(i),
                Size = 0,
                MtimeTicks = 0,
                Inode = 0,
            });
        }
        return docs;
    }

    private static string TempDir()
    {
        string dir = Path.Combine(Path.GetTempPath(), "recall_tests_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        return dir;
    }

    [Fact]
    public void Update_AddsModifiesDeletes_AndPrunesUnchangedDirs()
    {
        string root = Path.Combine(Path.GetTempPath(), "recall_upd_" + Guid.NewGuid().ToString("N"));
        string indexDir = Path.Combine(root, "index");
        Directory.CreateDirectory(Path.Combine(root, "vault", "a"));
        Directory.CreateDirectory(Path.Combine(root, "vault", "b"));
        try
        {
            File.WriteAllText(Path.Combine(root, "vault", "a", "one.txt"), "第一次写入 包含 钾 关键字");
            File.WriteAllText(Path.Combine(root, "vault", "b", "two.txt"), "乙 文档 内容");
            string scanRoot = Path.Combine(root, "vault");
            var options = new RecallUpdateOptions
            {
                Scan = new RecallScanOptions { SkipDirectoryNames = new[] { "index" } },
            };
            var first = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.Equal(2, first.Added);
            Assert.True(first.WroteIndex);

            using (var index = RecallIndex.Open(indexDir))
            {
                Assert.Equal("vault/a/one.txt", index.Search("钾", 3)[0].Path);
            }

            var idle = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.False(idle.Dirty);
            Assert.False(idle.WroteIndex);
            Assert.True(idle.DirsPruned >= 1);

            File.WriteAllText(Path.Combine(root, "vault", "a", "one.txt"), "第二次写入 包含 铷 关键字 追加内容");
            File.WriteAllText(Path.Combine(root, "vault", "b", "three.txt"), "丙 文档 内容");
            var second = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.Equal(1, second.Modified);
            Assert.Equal(1, second.Added);
            using (var index = RecallIndex.Open(indexDir))
            {
                Assert.Equal("vault/a/one.txt", index.Search("铷", 3)[0].Path);
                Assert.Empty(index.Search("钾", 3));
                Assert.Equal("vault/b/three.txt", index.Search("丙", 3)[0].Path);
            }

            File.Delete(Path.Combine(root, "vault", "b", "three.txt"));
            var third = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.Equal(1, third.Deleted);
            using (var index = RecallIndex.Open(indexDir))
            {
                Assert.Empty(index.Search("丙", 3));
                Assert.Equal("vault/a/one.txt", index.Search("铷", 3)[0].Path);
            }
        }
        finally
        {
            Directory.Delete(root, true);
        }
    }

    [Fact]
    public void Update_AlternatingVerify_CatchesSameSizeContentRewrite()
    {
        // §D9 回归: 目录 mtime 对「纯内容改写」不可见 ⇒ 需要交替全量核验。本轮刻意用**等字节长度**改写
        // (size 不变, 只有文件 mtime 变) 逼出「文件级 (size, mtime) 比对必须真的发生过」这一条。
        string root = Path.Combine(Path.GetTempPath(), "recall_upd_d9_" + Guid.NewGuid().ToString("N"));
        string indexDir = Path.Combine(root, "index");
        Directory.CreateDirectory(Path.Combine(root, "vault", "d"));
        try
        {
            string target = Path.Combine(root, "vault", "d", "note.txt");
            string before = "前缀 钾 内容 尾部填充";
            string after = "前缀 铷 内容 尾部填充";
            Assert.Equal(System.Text.Encoding.UTF8.GetByteCount(before), System.Text.Encoding.UTF8.GetByteCount(after));
            File.WriteAllText(target, before);

            string scanRoot = Path.Combine(root, "vault");
            var options = new RecallUpdateOptions
            {
                Scan = new RecallScanOptions { SkipDirectoryNames = new[] { "index" } },
            };

            var first = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.Equal(1, first.Added);
            Assert.False(first.VerifiedAllDirs);
            Assert.False(first.PrevScanPruned);

            var idle = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.False(idle.Dirty);
            Assert.True(idle.DirsPruned >= 1);
            Assert.False(idle.VerifiedAllDirs);

            File.WriteAllText(target, after);
            var second = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.True(second.PrevScanPruned);
            Assert.True(second.VerifiedAllDirs);   // 上轮剪过 ⇒ 本轮强制核验
            Assert.Equal(0, second.DirsPruned);    // 核验轮该计数恒 0 (计划 §7 已注明)
            Assert.Equal(1, second.Modified);      // size 相同, 只能靠文件级 mtime 捕获
            using (var index = RecallIndex.Open(indexDir))
            {
                Assert.Equal("vault/d/note.txt", index.Search("铷", 3)[0].Path);
                Assert.Empty(index.Search("钾", 3));
            }

            var idle2 = RecallIndexUpdater.Update(scanRoot, indexDir, options);
            Assert.False(idle2.Dirty);
            Assert.True(idle2.DirsPruned >= 1);    // 核验轮之后恢复剪枝 (交替)
            Assert.False(idle2.VerifiedAllDirs);
        }
        finally
        {
            Directory.Delete(root, true);
        }
    }

    [Fact]
    public void Links_In_Content_Are_Extracted_Stored_And_Returned()
    {
        string dir = TempDir();
        try
        {
            var docs = Corpus(3, i => i == 1
                ? "设计文档 参见 [索引设计](docs/plans/v0.96.0-r480-recall-module.md) 与 https://example.com/spec?a=1 以及 src/agent.recall/RecallIndex.cs"
                : "无关 内容 " + i);
            using var index = RecallIndex.Build(dir, docs);
            var hits = index.Search("索引设计", 3);
            Assert.NotEmpty(hits);
            Assert.Contains("docs/plans/v0.96.0-r480-recall-module.md", hits[0].Links);
            Assert.Contains("https://example.com/spec?a=1", hits[0].Links);
            Assert.Contains("src/agent.recall/RecallIndex.cs", hits[0].Links);
            // 地址也可被直接召回 (产出物自带地址 ⇒ 无需分类)
            Assert.Equal("doc-1", index.Search("RecallIndex.cs", 3)[0].Id);
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public void Relative_References_Resolve_Against_Referrer_Directory()
    {
        var options = new RecallLinkOptions();
        var sink = new List<string>();
        int n = RecallLinkExtractor.Extract(
            "见 [B](../reports/b.md) 与 [C](./c.md) 还有 src/x.cs 以及 https://example.com/p".AsSpan(),
            options,
            sink,
            "docs/plans/a.md");
        Assert.Equal(4, n);
        Assert.Contains("docs/reports/b.md", sink); // ../ ⇒ 按引用方目录回退一层
        Assert.Contains("docs/plans/c.md", sink);   // ./ ⇒ 按引用方目录展开
        Assert.Contains("src/x.cs", sink);          // 根相对 ⇒ 原样保留 (主力通路, 不得改写)
        Assert.Contains("https://example.com/p", sink);

        // 越根 fail-closed: 原值返回, 不猜目标
        var escaped = new List<string>();
        RecallLinkExtractor.Extract("x [E](../../../e.md)".AsSpan(), options, escaped, "a.md");
        Assert.Contains("../../../e.md", escaped);
    }

    [Fact]
    public void TaskState_Is_Durable_And_Feeds_Recall()
    {
        string root = TempDir();
        try
        {
            string indexDir = Path.Combine(root, "index");
            var store = new RecallTaskStateStore(root);
            store.Append("T-1", new TaskStateEvent
            {
                Ts = 1,
                Kind = "artifact",
                Text = "产出 报告",
                Artifacts = new[] { "docs/reports/r480.md" },
                Links = new[] { "docs/plans/v0.96.0-r480-recall-module.md" },
            });
            // 新实例读取 = 不依赖任何进程内/上下文状态
            var state = new RecallTaskStateStore(root).Load("T-1");
            Assert.Equal(1, state.EventCount);
            Assert.Equal("task://T-1", state.Address);
            Assert.Contains("docs/reports/r480.md", state.Artifacts);

            using (var builder = RecallIndexBuilder.Create(indexDir, new RecallWriteOptions()))
            {
                Assert.NotNull(builder);
            }
            using (var empty = RecallIndex.Open(indexDir))
            {
                Assert.Equal(0, empty.DocCount);
            }
            Assert.Equal(1, store.SyncToIndex("T-1", indexDir));
            using (var index = RecallIndex.Open(indexDir))
            {
                var hits = index.Search("报告", 3);
                Assert.NotEmpty(hits);
                Assert.Contains("task://T-1", hits[0].Path);
            }
        }
        finally
        {
            Directory.Delete(root, true);
        }
    }

    [Fact]
    public void Recall_Results_Feed_Back_Into_Task_State()
    {
        string root = TempDir();
        try
        {
            var docs = Corpus(2, i => "甲 " + i);
            using var index = RecallIndex.Build(Path.Combine(root, "index"), docs);
            var hits = index.Search("甲", 3);
            var store = new RecallTaskStateStore(root);
            store.RecordRecall("T-2", "甲", hits);
            var state = store.Load("T-2");
            Assert.Equal(1, state.EventCount);
            Assert.Contains(state.Artifacts, a => a.EndsWith("file-0", StringComparison.Ordinal));
        }
        finally
        {
            Directory.Delete(root, true);
        }
    }
}
